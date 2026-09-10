import os
import physicellpy as pc
from heterogeneity_setup_tissue import setup_tissue
from heterogeneity_coloring import heterogeneity_coloring_function


# pc.initialize("../PhysiCell-development/sample_projects/heterogeneity/config/PhysiCell_settings.xml")

# os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../user_projects/hetero"))
                       

pc.initialize("config/PhysiCell_settings.xml")

tumor_def = pc.find_cell_definition("cancer cell")

# custom.cpp's create_cell_types() sets these on pCD->parameters before
# setup_tissue() ever runs -- required so update_cell_and_death_parameters_O2_based's
# O2 multiplier is computed against this project's actual O2 level (~38) rather
# than PhysiCell's generic normoxic default (160), which otherwise suppresses
# proliferation to a small fraction of the intended rate and reads as cells
# "dying too fast" (they're not dying faster, they're barely dividing).
tumor_def.parameters.o2_proliferation_saturation = 38
tumor_def.parameters.o2_reference = 38

def tumor_cell_phenotype_with_oncoprotein(cell, phenotype, dt):
    pc.update_cell_and_death_parameters_O2_based(cell, phenotype, dt)

    if pc.get_single_signal(cell, "dead") > 0.5:
        cell.clear_update_phenotype()
        return

    cycle_rate = pc.get_single_behavior(cell, "cycle entry")
    cycle_rate *= pc.get_single_signal(cell, "custom:oncoprotein")
    pc.set_single_behavior(cell, "cycle entry", cycle_rate)

tumor_def.set_update_phenotype(tumor_cell_phenotype_with_oncoprotein)

cells = setup_tissue(pc)
# cells = []
# for i in range(10):
#     c = pc.create_cell(tumor_def)
#     c.position = [i * 15.0 - 75.0, 0.0, 0.0]
#     c.custom_data["oncoprotein"] = 0.5 + 0.1 * i  # vary it per cell like the C++ example's random draw
#     cells.append(c)


folder = pc.config_folder()
pc.svg_options.length_bar = 200
pc.set_svg_coloring_function(heterogeneity_coloring_function)

pc.save_svg(f"{folder}/initial.svg", cell_coloring="custom")
pc.save_svg_legend(f"{folder}/legend.svg", cell_coloring="custom")
pc.save_multicellds(f"{folder}/initial")

demo_max_time = 25920.0  # minutes (18 days - seen in PlosCompBio paper)
demo_max_time = 21600.0  # minutes (15 days)
demo_max_time = 120.0  # minutes

report_every = 120.0    # minutes
report_every = 30.0    # minutes

next_report = 0.0
output_index = 0

while pc.current_time() < demo_max_time:
    pc.run_simulation_step()

    if pc.current_time() >= next_report:
        # n_alive = sum(1 for c in pc.all_cells() if not c.phenotype.death.dead)
        # print(f"t = {pc.current_time():7.1f} min | cells = {len(pc.all_cells())} | alive = {n_alive}")
        print(f"t = {pc.current_time():7.1f} min ")

        pc.save_svg(f"{folder}/snapshot{output_index:08d}.svg", cell_coloring="custom")
        pc.save_multicellds(f"{folder}/output{output_index:08d}")
        output_index += 1
        next_report += report_every

# for c in cells:
#     print(f"cell {c.ID}: oncoprotein={c.custom_data['oncoprotein']:.2f}  "
#           f"secretion_rate(oxygen)={c.phenotype.secretion.secretion_rate('oxygen'):.3f}")
