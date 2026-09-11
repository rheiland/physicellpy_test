
import physicellpy as pc

pc.initialize("config/PhysiCell_settings.xml")
pc.setup_tissue()

folder = pc.config_folder()   # output folder
pc.svg_options.length_bar = 200
pc.save_svg(f"{folder}/initial.svg")
pc.save_svg_legend(f"{folder}/legend.svg")
pc.save_multicellds(f"{folder}/initial")

report_every = 120.0    # minutes
next_report = 0.0
output_index = 0

while pc.current_time() < pc.max_time():
    pc.run_simulation_step()

    if pc.current_time() >= next_report:
        n_alive = sum(1 for c in pc.all_cells() if not c.phenotype.death.dead)
        print(f"t = {pc.current_time():7.1f} min | "\
              f"cells = {len(pc.all_cells())} | alive = {n_alive}")

        pc.save_svg(f"{folder}/snapshot{output_index:08d}.svg")
        pc.save_multicellds(f"{folder}/output{output_index:08d}")
        output_index += 1
        next_report += report_every

