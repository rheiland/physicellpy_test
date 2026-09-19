# This example assumes you have run the template sample project 
# for its full 5 days max_time. This script will resume from the 
# final state and continue for another day. And it will write 
# output files into the same output dir as the original. 

import sys
import physicellpy as pc

print("-------- calling pc.initialize\n\n")
pc.initialize("config/PhysiCell_settings.xml")
# pc.setup_tissue()

print("-------- calling pc.resume_from_multicellds\n\n")
pc.resume_from_multicellds(pc.config_folder(), "output00000060.xml", create_cells=True, debug_print=True)

print(f"\n--------  after resume, current_time= {pc.current_time()} ")   # = 7200 for template project
# sys.exit()

folder = pc.config_folder()   # output folder

# don't need to do this if just continuing in the same output dir
# pc.svg_options.length_bar = 200
# pc.save_svg(f"{folder}/initial.svg")
# pc.save_svg_legend(f"{folder}/legend.svg")
# pc.save_multicellds(f"{folder}/initial")

report_every = 60.0    # match the save output "interval"
next_report = pc.current_time() + report_every
print(f"--------  next_report (time)= {next_report} ")

# set to whatever the original max output index was +1
output_index = 61

new_max_time = 8640  # whatever new end time you want

while pc.current_time() < new_max_time:
    pc.run_simulation_step()

    if pc.current_time() >= next_report:
        print(f"t = {pc.current_time():7.1f} min ")

        pc.save_svg(f"{folder}/snapshot{output_index:08d}.svg")
        pc.save_multicellds(f"{folder}/output{output_index:08d}")
        output_index += 1
        next_report += report_every
