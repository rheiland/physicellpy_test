
import physicellpy as pc
import math
import random

def h2o_update_phenotype(cell, phenotype, dt):
    # print(f'----- {pc.current_time}: # attachments={dir(cell)}')
    print(f'----- {pc.current_time()}:  # attached= {cell.number_of_attached_cells()}')
    # pc.update_cell_and_death_parameters_O2_based(cell, phenotype, dt)

    # if pc.get_single_signal(cell, "dead") > 0.5:
    #     cell.clear_update_phenotype()
    #     return

    # cycle_rate = pc.get_single_behavior(cell, "cycle entry")
    # cycle_rate *= pc.get_single_signal(cell, "custom:oncoprotein")
    # pc.set_single_behavior(cell, "cycle entry", cycle_rate)


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


pc.initialize("config/PhysiCell_settings.xml")

h2o_def = pc.find_cell_definition("h2o_source")
# callback fns must be set BEFORE defining ccells
h2o_def.set_update_phenotype(h2o_update_phenotype)

c = pc.create_cell(h2o_def)
c.is_movable = False
c.position = [0, 0, 0]

# pc.setup_tissue()
# phillic_def = pc.find_cell_definition("hydrophilic")
phobic_def = pc.find_cell_definition("hydrophilic")
# c= pc.create_cell(cell_def)
# c.position = [x, y, z]
create_cargo_cluster_6(phobic_def, 0, 0, z=0.0, spacing=None, rng=None)

folder = pc.config_folder()   # output folder
pc.svg_options.length_bar = 200
pc.save_svg(f"{folder}/initial.svg")
pc.save_svg_legend(f"{folder}/legend.svg")
pc.save_multicellds(f"{folder}/initial")


report_every = 30.0    # minutes
next_report = 0.0
output_index = 0

max_time = pc.current_time()
max_time = 10

while pc.current_time() < max_time:
    pc.step()

    if pc.current_time() >= next_report:
        n_alive = sum(1 for c in pc.all_cells() if not c.phenotype.death.dead)
        print(f"t = {pc.current_time():7.1f} min | "\
              f"cells = {len(pc.all_cells())} | alive = {n_alive}")
        # print(f"t = {pc.current_time():7.1f} min ")

        pc.save_svg(f"{folder}/snapshot{output_index:08d}.svg")
        pc.save_multicellds(f"{folder}/output{output_index:08d}")
        output_index += 1
        next_report += report_every

