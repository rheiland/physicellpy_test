
import math
import sys
import os
import physicellpy as pc

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from geom_ics_2D import create_hex_annulus, create_random_annulus

# L-system vessel-tree generator, ported from l-sys2.py's expand_l_system()
# and draw_coarse_vessels() -- same axiom/rules/geometry walk, but collecting
# (x0, y0, x1, y1, width) segments instead of plotting them.
def expand_l_system(axiom, rules, iterations):
    current = axiom
    for _ in range(iterations):
        current = "".join(rules.get(char, char) for char in current)
    return current


def l_system_vessel_segments(l_string, angle, initial_length=25.0, length_decay=0.8,
                              initial_width=8.0, width_decay=0.75):
    x, y = 0.0, 0.0
    curr_angle = 90.0
    length = initial_length
    width = initial_width
    stack = []
    segments = []

    for char in l_string:
        if char == 'F':
            next_x = x + length * math.cos(math.radians(curr_angle))
            next_y = y + length * math.sin(math.radians(curr_angle))
            segments.append((x, y, next_x, next_y, width))
            x, y = next_x, next_y
        elif char == '+':
            curr_angle += angle
        elif char == '-':
            curr_angle -= angle
        elif char == '[':
            stack.append((x, y, curr_angle, length, width))
            length *= length_decay
            width *= width_decay
        elif char == ']':
            x, y, curr_angle, length, width = stack.pop()

    return segments, initial_width


def _map_segments_to_domain(segments, bounding_box, margin=0.9):
    """Scale/translate the L-system's local-coordinate segments to fit
    inside the microenvironment's (x, y) bounding box, leaving `margin`
    fraction of the domain's extent occupied so the tree doesn't touch
    the domain edges."""
    xs = [s[0] for s in segments] + [s[2] for s in segments]
    ys = [s[1] for s in segments] + [s[3] for s in segments]
    local_xmin, local_xmax = min(xs), max(xs)
    local_ymin, local_ymax = min(ys), max(ys)
    local_w = max(local_xmax - local_xmin, 1e-6)
    local_h = max(local_ymax - local_ymin, 1e-6)

    xmin, ymin, _, xmax, ymax, _ = bounding_box
    domain_w = (xmax - xmin) * margin
    domain_h = (ymax - ymin) * margin
    scale = min(domain_w / local_w, domain_h / local_h)

    local_cx = (local_xmin + local_xmax) / 2.0
    local_cy = (local_ymin + local_ymax) / 2.0
    domain_cx = (xmin + xmax) / 2.0
    domain_cy = (ymin + ymax) / 2.0

    mapped = []
    for x0, y0, x1, y1, width in segments:
        mx0 = domain_cx + (x0 - local_cx) * scale
        my0 = domain_cy + (y0 - local_cy) * scale
        mx1 = domain_cx + (x1 - local_cx) * scale
        my1 = domain_cy + (y1 - local_cy) * scale
        mapped.append((mx0, my0, mx1, my1, width))
    return mapped


def _point_segment_distance(px, py, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq == 0.0:
        return math.hypot(px - x0, py - y0)
    t = max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / seg_len_sq))
    return math.hypot(px - (x0 + t * dx), py - (y0 + t * dy))


def vascular_network(microenv, idx_oxygen, oxy_value=40.0, *,
                      axiom="F", rules=None, iterations=3, angle=30.0,
                      initial_length=25.0, length_decay=0.8,
                      initial_width=8.0, width_decay=0.75, margin=0.9):
    """Mark the microenvironment voxels that fall along an L-system-generated
    vessel tree as Dirichlet oxygen sources, with each voxel's value scaled
    by the nearest vessel segment's width (thicker/root vessels -> more
    oxygen) -- the domain-mapped counterpart of l-sys2.py's plotted tree.

    The tree is generated in its own local coordinates, then scaled and
    centered to fill `margin` of microenv's actual (x, y) extent, so the
    same call produces a correctly-proportioned tree on any domain size --
    growing the domain changes the tree's absolute scale, not its shape.
    Use `iterations`/`angle`/the decay rates to change the shape itself,
    e.g. more iterations for a denser tree on a much larger domain."""
    if rules is None:
        rules = {"F": "F[+F][-F]F"}
    l_seq = expand_l_system(axiom, rules, iterations)
    segments, initial_width = l_system_vessel_segments(
        l_seq, angle, initial_length, length_decay, initial_width, width_decay)
    segments = _map_segments_to_domain(segments, microenv.bounding_box, margin)

    x_coords, y_coords, _ = microenv.mesh_axes
    nx, ny, nz = microenv.mesh_shape
    hit_threshold = 0.5 * (x_coords[1] - x_coords[0]) if nx > 1 else float("inf")

    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                best_width = None
                best_dist = hit_threshold
                for x0, y0, x1, y1, width in segments:
                    d = _point_segment_distance(x_coords[i], y_coords[j], x0, y0, x1, y1)
                    if d <= best_dist:
                        best_dist = d
                        best_width = width
                if best_width is not None:
                    voxel = (k * ny + j) * nx + i
                    microenv.update_dirichlet_node(
                        voxel, idx_oxygen, oxy_value * best_width / initial_width)

    # update_dirichlet_node() only marks the voxel/value; the density field
    # isn't actually updated until the next diffusion-decay solve step, so
    # force it now in case something (e.g. the initial.svg/multicellds save)
    # reads the field before the first pc.step().
    microenv.apply_dirichlet_conditions()


pc.initialize("config/PhysiCell_settings.xml")

microenv = pc.microenvironment
idx_oxygen = microenv.find_density_index("oxygen")

vascular_network(microenv, idx_oxygen)


# pc.setup_tissue() is physicellpy's own generic placement helper (it
# places parameters.ints("number_of_cells") of every cell type, which this
# config doesn't define) -- it is NOT custom.cpp's setup_tissue(), which
# instead places one cell of the first registered type at the origin. Port
# that explicitly, since skipping it leaves all_cells empty and crashes
# save_multicellds() (it indexes all_cells[0] unconditionally).
cell_def = pc.find_cell_definition(pc.cell_type_names()[0])
# cell = pc.create_cell(cell_def)
# cell.position = [0, 0, 0]

# cells = create_hex_annulus(pc.find_cell_definition("cancer") x0, y0, r1, r2, spacing)
# cells = create_hex_annulus(pc.find_cell_definition("cancer") 500, 0, 0, 100, 0.0)
# def create_hex_annulus(cell_definition, x0, y0, r1, r2, spacing=1.0, z=0.0, cell_radius=None):
cells = create_hex_annulus(cell_def, 500, 0, 0, 100, cell_radius=8)

folder = pc.config_folder()   # output folder
pc.svg_options.length_bar = 200
pc.save_svg(f"{folder}/initial.svg")
pc.save_svg_legend(f"{folder}/legend.svg")
pc.save_multicellds(f"{folder}/initial")

report_every = 1.0    # minutes
next_report = 0.0
output_index = 0

while pc.current_time() < pc.max_time():
    pc.step()

    if pc.current_time() >= next_report:
        n_alive = sum(1 for c in pc.all_cells() if not c.phenotype.death.dead)
        print(f"t = {pc.current_time():7.1f} min | "\
              f"cells = {len(pc.all_cells())} | alive = {n_alive}")

        pc.save_svg(f"{folder}/snapshot{output_index:08d}.svg")
        pc.save_multicellds(f"{folder}/output{output_index:08d}")
        output_index += 1
        next_report += report_every

