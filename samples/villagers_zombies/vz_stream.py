import os
import sys
import socket
import struct
import numpy as np
import physicellpy as pc
import random

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from geom_ics_2D import create_hex_annulus, create_random_annulus
# from run_isolated import DONE_MARKER

# os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../user_projects/villagers_zombies"))

random.seed(0)
pc.initialize("config/PhysiCell_settings.xml")

#         <cell_definition name="villager" ID="0">
#         <cell_definition name="zombie" ID="1">

villager_def = pc.find_cell_definition("villager")

villager_def.phenotype.volume.total = 5000.0   # set before creating cells

# def create_random_annulus(cell_definition, x0, y0, r1, r2, n, z=0.0, rng=None):
cells = create_random_annulus(villager_def, 0, 0, 0, 400, 200, z=0.0)

zombie_def = pc.find_cell_definition("zombie")
zombie_def.phenotype.volume.total = 5000.0   # set before creating cells
cells = create_random_annulus(zombie_def, 0, 0, 0, 400, 10, z=0.0, rng=None)

# NOTE: the config's own <cell_rules> block already loads
# user_projects/villagers_zombies/config/cell_rules.csv during initialize()
# (see setup_cell_rules(), called automatically). Do NOT call
# pc.read_rules() on that same file here -- re-adding a rule that already
# exists (same cell_type/signal/behavior/response) calls PhysiCell's own
# exit(-1) directly, killing the whole process with no exception and no
# traceback. Use pc.find_ruleset()/HypothesisRuleset.find_behavior() to
# inspect or edit the already-loaded rules instead, e.g.:
villager_ruleset = pc.find_ruleset(villager_def)
apoptosis_rule = villager_ruleset.find_behavior("apoptosis")
zombie_transform_rule = villager_ruleset.find_behavior("transform to zombie")
print(f"apoptosis rule: signals={apoptosis_rule.signals} "
      f"half_maxes={apoptosis_rule.half_maxes} hill_powers={apoptosis_rule.hill_powers} "
      f"max_value={apoptosis_rule.max_value}")
# edit an existing rule's Hill-function parameters:
apoptosis_rule.set_half_max("damage", 3.0)
# or via the free-function form, equivalent to the line above:
# pc.set_hypothesis_parameters("villager", "damage", "apoptosis", 3.0, 4.0)

print(f"placed {len(pc.all_cells())} cells")
print(f"dt = {pc.diffusion_dt()} min, config max_time = {pc.max_time()} min")

folder = pc.config_folder()
pc.svg_options.length_bar = 200

pc.save_svg(f"{folder}/initial.svg")
pc.save_svg_legend(f"{folder}/legend.svg")
pc.save_multicellds(f"{folder}/initial")

# Stream each reported frame as VTK-ready polydata (cell positions + a
# "CellType" scalar) so a separate VTK viewer can render the run live.
STREAM_HOST = '127.0.0.1'
STREAM_PORT = 56790

stream_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
stream_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
stream_server.bind((STREAM_HOST, STREAM_PORT))
stream_server.listen(1)
print(f"Waiting for viewer to connect on {STREAM_HOST}:{STREAM_PORT}...")
stream_conn, stream_addr = stream_server.accept()
print(f"Viewer connected from {stream_addr}")
streaming = True

print("Waiting for 'g' keypress in viewer window to start simulation...")
stream_conn.recv(1)
print("Go signal received -- starting simulation.")


def stream_frame():
    global streaming
    if not streaming:
        return

    positions = np.array([c.position for c in pc.all_cells()], dtype=np.float32)
    types = np.array([c.type for c in pc.all_cells()], dtype=np.float32)
    radii = np.array([c.phenotype.geometry.radius for c in pc.all_cells()], dtype=np.float32)

    header = struct.pack('!If', len(types), pc.current_time())
    try:
        stream_conn.sendall(header + positions.tobytes() + types.tobytes() + radii.tobytes())
    except OSError as exc:
        print(f"Viewer disconnected: {exc}")
        streaming = False


demo_max_time = 7200.0  # minutes
demo_max_time = 1440.0  # minutes
demo_max_time = 2880.0  # minutes
report_every = 5.0    # minutes
next_report = 0.0
output_index = 0
rule_flipped = False
# rule_flipped = True

# villager,contact with villager,increases,cycle entry,0.001,0.5,50,0
# villager,damage,increases,apoptosis,0.05,0.5,4,0
# villager,damage,increases,transform to zombie,0.01,0.5,4,0

while pc.current_time() < demo_max_time:
    pc.run_simulation_step()

    # if not rule_flipped and pc.current_time() > 400:
    if not rule_flipped and pc.current_time() > 500:
        # was: damage increases apoptosis, toward max_value=0.05
        # now: damage decreases apoptosis, toward min_value=0.0
        apoptosis_rule.set_response("damage", "decreases")
        apoptosis_rule.min_value = 0.0

        # was: damage increases transform to zombie, toward max_value=0.01
        # now: max_value=0.0 -- rate stays pinned at 0 for any damage level.
        # Response direction (still "increases") is left alone -- unlike
        # the apoptosis rule above, villagers just stop transforming
        # entirely rather than getting a symmetric "damage protects you"
        # effect in the other direction.
        zombie_transform_rule.max_value = 0.0

        rule_flipped = True
        print(f"t = {pc.current_time():7.1f} min | flipped apoptosis rule: "
              f"damage now decreases apoptosis toward {apoptosis_rule.min_value}; "
              f"disabled transform-to-zombie (max_value={zombie_transform_rule.max_value})")

    if pc.current_time() >= next_report:
        n_alive = sum(1 for c in pc.all_cells() if not c.phenotype.death.dead)
        print(f"t = {pc.current_time():7.1f} min | cells = {len(pc.all_cells())} | alive = {n_alive}")

        stream_frame()

        # pc.save_svg(f"{folder}/snapshot{output_index:08d}.svg")
        # pc.save_multicellds(f"{folder}/output{output_index:08d}")
        output_index += 1
        next_report += report_every

stream_conn.close()
stream_server.close()

# print(f"done -- wrote {output_index} snapshot(s) to {folder}/")
print(f"done -- computed {output_index} frames")
# print(DONE_MARKER)