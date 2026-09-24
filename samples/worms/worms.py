
import math
import random
import physicellpy as pc
import xml.etree.ElementTree as ET

def chemotaxis_function(cell, phenotype, dt):
    # PhysiCell's standard chemotaxis_function: bias direction is the
    # gradient of the chemotaxis substrate, signed by chemotaxis_direction, normalized
    m = phenotype.motility
    g = cell.nearest_gradient(m.chemotaxis_index)
    v = [x * m.chemotaxis_direction for x in g]
    norm = sum(x * x for x in v) ** 0.5
    m.migration_bias_direction = [x / norm for x in v] if norm > 1e-16 else v


def head_migration_direction(cell, phenotype, dt):
    phenotype.motility.chemotaxis_direction = int(pc.parameters.doubles("head_migration_direction"))
    phenotype.motility.migration_speed = pc.parameters.doubles("head_migration_speed")
    phenotype.motility.migration_bias = pc.parameters.doubles("head_migration_bias")
    phenotype.motility.persistence_time = pc.parameters.doubles("head_migration_persistence")
    chemotaxis_function(cell, phenotype, dt)


def tail_migration_direction(cell, phenotype, dt):
    phenotype.motility.chemotaxis_direction = int(pc.parameters.doubles("tail_migration_direction"))
    phenotype.motility.migration_speed = pc.parameters.doubles("tail_migration_speed")
    phenotype.motility.migration_bias = pc.parameters.doubles("tail_migration_bias")
    phenotype.motility.persistence_time = pc.parameters.doubles("tail_migration_persistence")
    chemotaxis_function(cell, phenotype, dt)


def middle_migration_direction(cell, phenotype, dt):
    # get velocity from "upstream"
    a0, a1 = cell.state.attached_cells[0], cell.state.attached_cells[1]
    upstream = a1 if a1.custom_data["head"] > a0.custom_data["head"] else a0

    phenotype.motility.migration_speed = pc.parameters.doubles("middle_migration_speed")
    v = list(upstream.phenotype.motility.migration_bias_direction)
    norm = sum(x * x for x in v) ** 0.5
    phenotype.motility.migration_bias_direction = [x / norm for x in v] if norm > 0 else v

#------- a callback function
def custom_function(cell, phenotype, dt):
    number_of_attachments = cell.state.number_of_attached_cells()

    # look for cells to form attachments, if 0 attachments
    if number_of_attachments == 0:
        max_attachments = int(cell.custom_data["max_attachments"])
        for other in cell.nearby_interacting_cells():
            if number_of_attachments >= max_attachments:
                break
            if other.state.number_of_attached_cells() < other.custom_data["max_attachments"]:
                pc.attach_cells(other, cell)
                number_of_attachments += 1

    # if no attachments, use chemotaxis
    if number_of_attachments == 0:
        cell.set_update_migration_bias(chemotaxis_function)

    # if 1 attachment, do some logic
    if number_of_attachments == 1:
        # constant expression in end cells
        cell.custom_data["head"] = cell.custom_data["head_initial"]

        # am I the head?
        head = cell.custom_data["head"] > cell.state.attached_cells[0].custom_data["head"]
        cell.set_update_migration_bias(head_migration_direction if head else tail_migration_direction)
        phenotype.secretion.set_secretion_rate("signal", 100)
        cell.set_internal_uptake_constants(pc.diffusion_dt())

    # if 2 or more attachments, use middle
    if number_of_attachments > 1:
        cell.set_update_migration_bias(middle_migration_direction)
        phenotype.secretion.set_secretion_rate("signal", 1)
        cell.set_internal_uptake_constants(pc.diffusion_dt())


def contact_function(me, pheno_me, other, pheno_other, dt):
    # PhysiCell calls this once per cell in me.state.attached_cells

    # spring-like adhesion
    pc.standard_elastic_contact_function(me, pheno_me, other, pheno_other, dt)

    # juxtacrine: transfer "head" from the higher to the lower cell.
    # Only high -> low, so one cell of each pair does the transfer.
    if me.state.number_of_attached_cells() > 0:
        head_me = me.custom_data["head"]
        head_other = other.custom_data["head"]
        if head_me > head_other:
            amount = dt * me.custom_data["transfer_rate"] * (head_me - head_other)
            me.custom_data["head"] = head_me - amount
            other.custom_data["head"] = other.custom_data["head"] + amount


def my_coloring_function(cell):
    # returns [cytoplasm fill, cytoplasm outline, nucleus fill, nucleus outline]
    n = cell.state.number_of_attached_cells()

    if n == 0:
        return ["grey", "black", "grey", "grey"]

    if n == 1:
        if cell.custom_data["head"] > cell.state.attached_cells[0].custom_data["head"]:
            return ["red", "black", "red", "red"]
        return ["orange", "black", "orange", "orange"]

    # 2 or more attachments: shaded by head protein value
    intensity = int(math.floor(255.0 * cell.custom_data["head"]))
    color = f"rgb({intensity},{intensity},255)"
    if n > 2:
        return ["yellow", "black", color, color]
    return [color, "black", color, color]


#---------------------------------------------
# Note: this boolean is true (and usually false):        
# <disable_automated_spring_adhesions>true</...>
config_file = "config/PhysiCell_settings.xml"
pc.initialize(config_file)

worm_def = pc.find_cell_definition("worm")

# define custom callback functions for desired behaviors
worm_def.set_custom_cell_rule(custom_function)
worm_def.set_contact_function(contact_function)

# get attachment_elastic_constant from user param
worm_def.phenotype.mechanics.attachment_elastic_constant = pc.parameters.doubles("attachment_elastic_constant")

pc.setup_tissue()

# mimic what's done in the C++ setup_tissue:
# random.seed(<n>) 
for c in pc.all_cells():
    c.custom_data["head"] = random.random()
    c.custom_data["head_initial"] = c.custom_data["head"]


full_data_interval = float(ET.parse(config_file).find("save/full_data/interval").text)
svg_data_interval = float(ET.parse(config_file).find("save/SVG/interval").text)

folder = pc.config_folder()   # output folder
pc.svg_options.length_bar = 200
pc.set_svg_coloring_function(my_coloring_function)
pc.save_svg(f"{folder}/initial.svg", cell_coloring="custom")
pc.save_svg_legend(f"{folder}/legend.svg", cell_coloring="custom")
pc.save_multicellds(f"{folder}/initial")

# report_every = 120.0    # minutes
report_every = svg_data_interval
next_report = 0.0
output_index = 0

while pc.current_time() < pc.max_time():
    pc.run_simulation_step()

    if pc.current_time() >= next_report:
        n_alive = sum(1 for c in pc.all_cells() if not c.phenotype.death.dead)
        print(f"t = {pc.current_time():7.1f} min | "\
              f"cells = {len(pc.all_cells())} | alive = {n_alive}")

        pc.save_svg(f"{folder}/snapshot{output_index:08d}.svg", cell_coloring="custom")
        pc.save_multicellds(f"{folder}/output{output_index:08d}")
        output_index += 1
        next_report += report_every

