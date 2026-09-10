"""Test simulation exercising the PhysiMeSS bindings (see
physimess_bindings.cpp): ECM fibres as agents alongside ordinary cells.

Uses the reference config from PhysiCell-development's own
sample_projects/physimess/config/Fibre_Initialisation/ -- a domain seeded
with number_of_fibres=2000 randomly placed, randomly oriented fibres (the
"ecm" CellDefinition) and no regular cells (number_of_cells=0). Mirrors
that sample project's own custom.cpp create_cell_types()/setup_tissue(),
just in Python: physicellpy's create_cell() already dispatches through
Cell_Definition.functions.instantiate_cell if set (core/PhysiCell_cell.cpp),
so setup_physimess_cell_definition() below is the only PhysiMeSS-specific
step -- everything after that is ordinary create_cell()/assign_position().
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import physicellpy as pc
# from geom_ics_2D import create_random_annulus  # noqa: F401 (not used here, kept for parity with other tests/ scripts)

# Same CWD requirement seen with villagers_zombies.py -- PhysiCell resolves
# the config's own relative <folder> paths against the process's working
# directory, not the config file's location.
# os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    #    "../PhysiCell-development/sample_projects/physimess"))

# pc.initialize("config/Fibre_Initialisation/mymodel_initialisation.xml")
pc.initialize("config/Fibre_Degradation/mymodel_fibre_degradation.xml")
# -- create cd for  attractant
# -- create cd for  ecm
# -- create cd for  cell


# pc.initialize("config/Cell_Fibre_Mechanics/mymodel_pushing.xml")

# Wire every registered CellDefinition up for PhysiMeSS -- equivalent to
# the cd->functions.xxx = ... lines in every PhysiMeSS sample project's own
# create_cell_types(). Must happen before any create_cell() calls:
# instantiate_cell is read once, at creation time.
pc.setup_physimess_cell_definition(pc.cell_defaults, is_fibre=False)
for cd_name in pc.cell_type_names():
    cd = pc.find_cell_definition(cd_name)
    print("-- create cd for ",cd_name)
    if not pc.is_fibre:
        print("-- it is NOT a fibre!")
    pc.setup_physimess_cell_definition(cd, is_fibre=pc.is_fibre(cd))

Xmin, Ymin, Zmin, Xmax, Ymax, Zmax = pc.microenvironment.bounding_box
if pc.simulate_2D():
    Zmin = Zmax = 0.0

import random
random.seed(0)

cell_def = pc.find_cell_definition("cell")
cell = pc.create_cell(cell_def)
cell.position = [0,0,0]

attractant_def = pc.find_cell_definition("attractant")
att = pc.create_cell(attractant_def)
att.position = [85,190,0]


n_fibres = pc.parameters.ints("number_of_fibres")
fibre_def = pc.find_cell_definition("ecm")
fibres = []
for _ in range(n_fibres):
    position = [
        Xmin + random.random() * (Xmax - Xmin),
        Ymin + random.random() * (Ymax - Ymin),
        Zmin + random.random() * (Zmax - Zmin),
    ]
    fibre = pc.create_cell(fibre_def)
    fibre.assign_fibre_orientation()
    fibre.check_out_of_bounds(position)
    fibre.position = position
    fibres.append(fibre)

pc.remove_physimess_out_of_bounds_fibres()
print(f"placed {n_fibres} fibres, {len(pc.all_cells())} remain after removing out-of-bounds ones")

folder = pc.config_folder()
pc.svg_options.length_bar = 200
pc.save_svg(f"{folder}/initial.svg")
pc.save_svg_legend(f"{folder}/legend.svg")

# This config's own <max_time> is 0 (a placement-only reference example) --
# run a short window here instead, just to prove physimess_mechanics()
# (neighbor/crosslink tracking) runs without error, not to show fibre
# dynamics developing (there are no motile cells in this scenario to move
# and interact with the fibres).
demo_max_time = 60.0
report_every = 20.0
next_report = 0.0
output_index = 0

while pc.current_time() < demo_max_time:
    # Matches main.cpp's own call order: physimess_mechanics() before
    # run_simulation_step(), both driven every diffusion step.
    pc.physimess_mechanics(pc.mechanics_dt())
    pc.run_simulation_step()

    if pc.current_time() >= next_report:
        n = len(pc.all_cells())
        print(f"t = {pc.current_time():7.1f} min | agents = {n}")
        pc.save_svg(f"{folder}/snapshot{output_index:08d}.svg")
        output_index += 1
        next_report += report_every

print(f"done -- wrote {output_index} snapshot(s) to {folder}/")
