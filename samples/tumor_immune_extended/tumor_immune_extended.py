
import shutil
import physicellpy as pc
import xml.etree.ElementTree as ET

config_file = "config/PhysiCell_settings.xml"
pc.initialize(config_file)
pc.setup_tissue()

full_data_interval = float(ET.parse(config_file).find("save/full_data/interval").text)

folder = pc.config_folder()   # output folder
print(f"--- output folder={folder}")
shutil.copy(config_file, folder)

pc.svg_options.length_bar = 200
pc.save_svg(f"{folder}/initial.svg")
pc.save_svg_legend(f"{folder}/legend.svg")
pc.save_multicellds(f"{folder}/initial")

report_every = full_data_interval  # assume full and SVG intervals equal
report_every = 720  # assume full and SVG intervals equal
next_report = 0.0
output_index = 0

while pc.current_time() < pc.max_time():
    pc.run_simulation_step()

    if pc.current_time() >= next_report:
        num_cells = sum(1 for c in pc.all_cells())
        # n_alive = sum(1 for c in pc.all_cells() if not c.phenotype.death.dead)
        # print(f"t = {pc.current_time():7.1f} min | "\
            #   f"cells = {len(pc.all_cells())} | alive = {n_alive}")
        print(f"current time: {pc.current_time():7.1f} min (max: {pc.max_time()})")
        print(f"total agents: {num_cells}")

# current simulated time: 1440 min (max: 1440 min)
# total agents: 543
# interval wall time: 0 days, 0 hours, 0 minutes, and 0.641867 seconds
# total wall time: 0 days, 0 hours, 0 minutes, and 32.2355 seconds


        pc.save_svg(f"{folder}/snapshot{output_index:08d}.svg")
        pc.save_multicellds(f"{folder}/output{output_index:08d}")
        output_index += 1
        next_report += report_every

