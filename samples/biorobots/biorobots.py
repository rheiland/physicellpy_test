import math
import os
import sys
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import physicellpy as pc
import random

# (x_min, y_min, z_min, x_max, y_max, z_max), set right after pc.initialize().
DOMAIN_BOUNDS = None


def clamp_position(cell):
    """Keep a cell's position inside the domain.

    PhysiCell's own virtual_wall_at_domain_edge does not appear to engage in
    this project: a cell placed just past the boundary with motility
    disabled was observed to sit there indefinitely with zero inward push.
    Once outside the mesh, signal-gradient lookups go degenerate (flat), and
    combined with a migration_bias of 1.0 (no randomness) a cell that drifts
    out gets permanently stuck -- this was the actual cause of workers that
    attach to cargo but then never chemotax to a director. This clamp is a
    safety net, not a physically accurate wall.
    """
    x_min, y_min, _, x_max, y_max, _ = DOMAIN_BOUNDS
    x, y, z = cell.position
    clamped_x = min(max(x, x_min), x_max)
    clamped_y = min(max(y, y_min), y_max)
    if clamped_x != x or clamped_y != y:
        cell.position = [clamped_x, clamped_y, z]


def clamp_position_rule(cell, phenotype, dt):
    clamp_position(cell)


def director_cell_rule(cell, phenotype, dt):
    """Direct port of custom_biobots.cpp's director_cell_rule() -- a no-op
    in the original too; director cells only act via their constant
    "director signal" secretion, configured in the XML.
    """
    return


def worker_cell_rule(cell, phenotype, dt):
    """Direct port of custom_biobots.cpp's worker_cell_rule(), using the
    real pc.attach_cells()/pc.detach_cells()/cell.attached_cells and
    cell.cells_in_my_container() bindings. The actual physical dragging of
    attached cargo is handled separately by worker_drag_cargo() below, not
    by a contact_function -- see that function's docstring for why.

    Unlike the C++ original, the chemotaxis/migration-bias behaviors are
    re-asserted on every call based on current attachment state, not just
    at the attach/detach transition. This project's cell_rules.csv also
    loads a rule for worker cells ("cargo signal increases chemotactic
    response to cargo signal") that HypothesisRule.apply() confirms runs
    automatically once per rules update, independent of this function --
    it keeps nudging "chemotactic response to cargo signal" back up
    whenever a worker is near any (still-secreting) cargo signal source,
    fighting a one-time override made only at the moment of attachment. A
    worker that had just attached, and is therefore right next to cargo
    signal, would otherwise start drifting back toward cargo instead of
    heading straight for a director.
    """
    threshold = pc.parameters.doubles("drop_threshold")
    attached_worker_migration_bias = pc.parameters.doubles("attached_worker_migration_bias")
    unattached_worker_migration_bias = pc.parameters.doubles("unattached_worker_migration_bias")
    elastic_coefficient = pc.parameters.doubles("elastic_coefficient")

    director_signal = pc.get_single_signal(cell, "director signal")

    pc.set_single_behavior(cell, "cell-cell adhesion elastic constant", elastic_coefficient)

    # Have I arrived? If so, release my cargo.
    if director_signal > threshold and cell.number_of_attached_cells() > 0:
        # set receptor = 0 for cells we're detaching from, and set their
        # cycle rate to zero
        for attached in cell.attached_cells:
            pc.set_single_behavior(attached, "custom:receptor", 0.0)
            pc.set_single_behavior(attached, "cycle entry", 0.0)

        cell.remove_all_attached_cells()

    # Am I searching for cargo? If so, see if I've found it.
    if cell.number_of_attached_cells() == 0:
        for other in cell.cells_in_my_container():
            # cells_in_my_container() includes the calling cell itself, and
            # this project's XML defaults "receptor" to 1 for worker cells
            # too (not just cargo) -- so unlike the C++ original, this port
            # must explicitly restrict docking to cargo cells, or workers
            # dock onto themselves/each other.
            if other.type_name != "cargo cell":
                continue
            # if it is expressing the receptor, dock with it
            receptor = pc.get_single_signal(other, "custom:receptor")
            if receptor > 0.5:
                pc.attach_cells(cell, other)
                pc.set_single_behavior(other, "custom:receptor", 0.0)

                pc.set_single_behavior(other, "director signal secretion", 0.0)
                pc.set_single_behavior(other, "cargo signal secretion", 0.0)

                # Unlike the C++ original (which keeps scanning and can
                # dock with every receptor-expressing cell in the
                # container), this port stops at the first cargo cell
                # found: cargo cells sit in tightly-packed
                # create_cargo_cluster_7() clusters here, and docking with
                # several siblings at once yanks them all toward the
                # worker simultaneously, which was observed in testing to
                # tear the cluster apart violently.
                break

    # Set chemotaxis weights and migration bias for whichever mode I'm
    # currently in -- every call, not just on the attach/detach
    # transition, to keep overriding the cargo-signal rule described above.
    if cell.number_of_attached_cells() > 0:
        pc.set_single_behavior(cell, "chemotactic response to director signal", 1.0)
        pc.set_single_behavior(cell, "chemotactic response to cargo signal", 0.0)
        pc.set_single_behavior(cell, "migration bias", attached_worker_migration_bias)
    else:
        pc.set_single_behavior(cell, "chemotactic response to director signal", 0.0)
        pc.set_single_behavior(cell, "chemotactic response to cargo signal", 1.0)
        pc.set_single_behavior(cell, "migration bias", unattached_worker_migration_bias)


# Caps how far worker_drag_cargo may move a cargo cell in one mechanics
# step, matching a normal cell's own per-step motion scale (migration_speed
# * dt_mechanics is well under 1 micron here).
#
# physicellpy exposes attach_cells()/cell.attached_cells but no settable
# cell.velocity, so there's no way to add a proper spring force into the
# same velocity accumulator PhysiCell's own adhesion/repulsion mechanics
# use. Registering elastic pull as a contact_function (called once per
# attached neighbor per mechanics step) instead moves position directly,
# stacking on top of -- rather than being resolved together with -- the
# engine's own repulsion. When a worker docks with cargo while still deep
# in its normal repulsion range (which can happen right at simulation
# start, since setup_tissue() scatters cells with no collision avoidance,
# or whenever the every-dt_phenotype worker_cell_rule() check happens to
# fire while a worker is mid-approach), that repulsion easily outweighs a
# capped position nudge and flings the pair apart instead of settling them
# together -- this was observed in testing and is what a contact_function
# can't avoid without a real velocity contribution.
#
# So dragging is approximated the same way the original WORKER_ATTACHMENTS
# version did: directly nudge the attached cargo's position each mechanics
# step, capped, one-directional (only cargo moves toward worker, not vice
# versa) -- gentler and more stable than fighting repulsion symmetrically.
MAX_DRAG_STEP = 0.5


def worker_drag_cargo(cell, phenotype, dt):
    """Not part of the C++ original -- see MAX_DRAG_STEP's docstring above
    for why dragging can't be a contact_function here. Nudges any cargo in
    cell.attached_cells toward cell every mechanics step (dt_mechanics,
    ~0.1 min); worker_cell_rule only runs every dt_phenotype (~6 min), far
    too infrequently for smooth motion. Registered as a custom_cell_rule
    specifically for this more frequent cadence.

    Also does this cell's clamp_position() -- workers can only have one
    custom_cell_rule registered, so the domain-edge safety net (see
    clamp_position()'s docstring) is folded in here instead of being a
    separate rule like director/cargo cells get.
    """
    clamp_position(cell)

    elastic_coefficient = pc.parameters.doubles("elastic_coefficient")
    wx, wy, wz = cell.position
    for attached_cargo in cell.attached_cells:
        cx, cy, cz = attached_cargo.position
        dx = elastic_coefficient * (wx - cx) * dt
        dy = elastic_coefficient * (wy - cy) * dt
        dz = elastic_coefficient * (wz - cz) * dt
        step_size = math.sqrt(dx * dx + dy * dy + dz * dz)
        if step_size > MAX_DRAG_STEP:
            scale = MAX_DRAG_STEP / step_size
            dx *= scale
            dy *= scale
            dz *= scale
        attached_cargo.position = [cx + dx, cy + dy, cz + dz]
        clamp_position(attached_cargo)


def create_cargo_cluster_6(cargo_definition, x0, y0, z=0.0, spacing=None, rng=None):
    """Create a hollow ring of 6 cargo cells centered at (x0, y0), with a
    random overall orientation.

    Port of custom_biobots.cpp's create_cargo_cluster_6(). spacing defaults
    to 0.95 * 2 * cargo_definition's configured radius (cells just
    touching), matching the C++ default.

    Returns the list of created Cell objects.
    """
    rand = rng if rng is not None else random
    if spacing is None:
        spacing = 0.95 * cargo_definition.phenotype.geometry.radius * 2.0
    d_theta = 2.0 * math.pi / 6.0
    theta = rand.uniform(0.0, 2.0 * math.pi)

    cells = []
    for _ in range(6):
        c = pc.create_cell(cargo_definition)
        c.position = [x0 + spacing * math.cos(theta), y0 + spacing * math.sin(theta), z]
        cells.append(c)
        theta += d_theta
    return cells


def create_cargo_cluster_7(cargo_definition, x0, y0, z=0.0, spacing=None, rng=None):
    """Create a filled cluster of 7 cargo cells at (x0, y0): a
    create_cargo_cluster_6() ring plus one cell at the center.

    Port of custom_biobots.cpp's create_cargo_cluster_7().

    Returns the list of created Cell objects.
    """
    cells = create_cargo_cluster_6(cargo_definition, x0, y0, z=z, spacing=spacing, rng=rng)
    center_cell = pc.create_cell(cargo_definition)
    center_cell.position = [x0, y0, z]
    cells.append(center_cell)
    return cells


def create_cargo_cluster_3(cargo_definition, x0, y0, z=0.0, spacing=None, rng=None):
    """Create a small cluster of 3 cargo cells centered at (x0, y0), with a
    random overall orientation.

    Port of custom_biobots.cpp's create_cargo_cluster_3(). spacing defaults
    to 0.95 * cargo_definition's configured radius, matching the C++
    default.

    Returns the list of created Cell objects.
    """
    rand = rng if rng is not None else random
    if spacing is None:
        spacing = 0.95 * cargo_definition.phenotype.geometry.radius * 1.0
    d_theta = 2.0 * math.pi / 3.0
    theta = rand.uniform(0.0, 2.0 * math.pi)

    cells = []
    for _ in range(3):
        c = pc.create_cell(cargo_definition)
        c.position = [x0 + spacing * math.cos(theta), y0 + spacing * math.sin(theta), z]
        cells.append(c)
        theta += d_theta
    return cells


def robot_coloring_function(cell):
    """Port of custom_biobots.cpp's robot_coloring_function(): colors cells
    by role (worker/cargo/director, from the worker_color/cargo_color/
    director_color user parameters) rather than PhysiCell's default
    by-cell-type palette. Dead cells render solid black, matching the C++.
    """
    if cell.phenotype.death.dead:
        return ["black", "black", "black", "black"]

    worker_id = pc.find_cell_definition("worker cell").type
    cargo_id = pc.find_cell_definition("cargo cell").type
    director_id = pc.find_cell_definition("director cell").type

    if cell.type == worker_id:
        color = pc.parameters.strings("worker_color")
    elif cell.type == cargo_id:
        color = pc.parameters.strings("cargo_color")
    elif cell.type == director_id:
        color = pc.parameters.strings("director_color")
    else:
        color = "white"

    # [cytoplasm_fill, cytoplasm_outline, nucleus_fill, nucleus_outline] --
    # matches the C++ exactly: outline stays black, no nucleus outline drawn.
    return [color, "black", color, "none"]


def setup_tissue():
    """Port of custom_biobots.cpp's setup_tissue(): places a configurable
    number of each cell type fully at random (number_of_cells, 0 by
    default), then seeds director cells down the domain's vertical
    midsection, scatters cargo (as loose singles or create_cargo_cluster_7()
    clusters) and worker cells along the fringes.
    """
    x_min, y_min, _, x_max, y_max, _ = pc.microenvironment.bounding_box
    x_range = x_max - x_min
    y_range = y_max - y_min

    director_def = pc.find_cell_definition("director cell")
    cargo_def = pc.find_cell_definition("cargo cell")
    worker_def = pc.find_cell_definition("worker cell")

    number_of_cells = pc.parameters.ints("number_of_cells")
    for cell_definition in (director_def, cargo_def, worker_def):
        print(f"Placing cells of type {cell_definition.name} ...")
        for _ in range(number_of_cells):
            c = pc.create_cell(cell_definition)
            c.position = [x_min + random.uniform(0.0, 1.0) * x_range,
                          y_min + random.uniform(0.0, 1.0) * y_range, 0.0]
    print()

    number_of_directors = pc.parameters.ints("number_of_directors")
    number_of_cargo_clusters = pc.parameters.ints("number_of_cargo_clusters")
    number_of_workers = pc.parameters.ints("number_of_workers")

    relative_margin = 0.2
    relative_outer_margin = 0.02

    print("Placing cells ...")

    print(f"\tPlacing {number_of_directors} director cells ...")
    for _ in range(number_of_directors):
        x = x_min + x_range * (relative_margin + (1.0 - 2 * relative_margin) * random.uniform(0.0, 1.0))
        y = y_min + y_range * (relative_outer_margin + (1.0 - 2 * relative_outer_margin) * random.uniform(0.0, 1.0))
        c = pc.create_cell(director_def)
        c.position = [x, y, 0.0]
        pc.set_single_behavior(c, "movable", 0.0)

    print("\tPlacing cargo cells ...")
    for _ in range(number_of_cargo_clusters):
        x = x_min + x_range * (relative_outer_margin + (1 - 2.0 * relative_outer_margin) * random.uniform(0.0, 1.0))
        y = y_min + y_range * (relative_outer_margin + (1 - 2.0 * relative_outer_margin) * random.uniform(0.0, 1.0))
        if random.uniform(0.0, 1.0) < 0.5:
            c = pc.create_cell(cargo_def)
            c.position = [x, y, 0.0]
        else:
            create_cargo_cluster_7(cargo_def, x, y)

    print("\tPlacing worker cells ...")
    for _ in range(number_of_workers):
        x = x_min + x_range * (relative_margin + (1.0 - 2 * relative_margin) * random.uniform(0.0, 1.0))
        y = y_min + y_range * (relative_outer_margin + (1.0 - 2 * relative_outer_margin) * random.uniform(0.0, 1.0))
        c = pc.create_cell(worker_def)
        c.position = [x, y, 0.0]

    print("done!")

    pc.load_cells_from_pugixml()


random.seed(0)
pc.initialize("config/PhysiCell_settings.xml")
# pc.initialize("config/small_model.xml")

DOMAIN_BOUNDS = pc.microenvironment.bounding_box

director_def = pc.find_cell_definition("director cell")
director_def.set_update_phenotype(director_cell_rule)
director_def.set_custom_cell_rule(clamp_position_rule)

cargo_def = pc.find_cell_definition("cargo cell")
cargo_def.set_custom_cell_rule(clamp_position_rule)

worker_def = pc.find_cell_definition("worker cell")
worker_def.set_update_phenotype(worker_cell_rule)
worker_def.set_custom_cell_rule(worker_drag_cargo)

pc.set_svg_coloring_function(robot_coloring_function)

setup_tissue()  # doing it in Python, not wrapped C++


print(f"placed {len(pc.all_cells())} cells")
print(f"dt = {pc.diffusion_dt()} min, config max_time = {pc.max_time()} min")

folder = pc.config_folder()
pc.svg_options.length_bar = 200

pc.save_svg(f"{folder}/initial.svg", cell_coloring="custom")
pc.save_svg_legend(f"{folder}/legend.svg", cell_coloring="custom")
pc.save_multicellds(f"{folder}/initial")

demo_max_time = 360.0  # minutes
report_every = 3.0    # minutes  (=2 in .xml)
next_report = 0.0
output_index = 0

# while pc.current_time() < demo_max_time:
while pc.current_time() < pc.max_time():
    pc.run_simulation_step()

    if pc.current_time() >= next_report:
        n_alive = sum(1 for c in pc.all_cells() if not c.phenotype.death.dead)
        print(f"t = {pc.current_time():7.1f} min | cells = {len(pc.all_cells())} | alive = {n_alive}")

        pc.save_svg(f"{folder}/snapshot{output_index:08d}.svg", cell_coloring="custom")
        pc.save_multicellds(f"{folder}/output{output_index:08d}")
        output_index += 1
        next_report += report_every

print(f"done -- wrote {output_index} snapshot(s) to {folder}/")
# print(DONE_MARKER)