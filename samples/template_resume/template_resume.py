# This example assumes you have run the template sample project 
# for its full 5 days max_time. This script will resume from the 
# final state and continue for another day. And it will write 
# output files into the same output dir as the original. 

import sys
import physicellpy as pc

print("-------- calling pc.initialize\n\n")


pc.initialize("config/PhysiCell_settings.xml")

checkpoint_file = "output00000060.xml"
pc.resume_from_multicellds(pc.config_folder(), checkpoint_file, 
                           create_cells=True, debug_print=True)

print(f"\n---  after resume, current_time= {pc.current_time()} ")       # = 7200 for template 
# sys.exit()  # exit if you just want to check state

folder = pc.config_folder()   # output folder

report_every = 60.0    # mins
next_report = pc.current_time() + report_every
print(f"--------  next_report (time)= {next_report} ")

# set to whatever the original max output index was +1
output_index = 61
new_max_time = 8640  # whatever new end time you want

while pc.current_time() < new_max_time:
    pc.step()

    if pc.current_time() >= next_report:
        print(f"t = {pc.current_time():7.1f} min ")

        pc.save_svg(f"{folder}/snapshot{output_index:08d}.svg")
        pc.save_multicellds(f"{folder}/output{output_index:08d}")
        output_index += 1
        next_report += report_every
