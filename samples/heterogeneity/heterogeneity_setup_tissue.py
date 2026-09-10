"""
Python port of setup_tissue() from
PhysiCell-development/sample_projects/heterogeneity/custom_modules/custom.cpp:

  - place one cell of every registered type at a random position (generic part)
  - hex-pack "cancer cell" tumor cells inside a circle of radius tumor_radius,
    mirroring the base point (x, y) into all four quadrants
  - assign each tumor cell a random custom_data["oncoprotein"] value, drawn
    from a normal distribution and clamped to [oncoprotein_min, oncoprotein_max]
  - print an oncoprotein mean/stdev/[min max] summary across all_cells()
  - load_cells_from_pugixml() for any config-specified CSV placement

Requires pc.parameters, pc.simulate_2D(), Geometry.radius, and
microenvironment.bounding_box/load_cells_from_pugixml() bindings added
alongside this script -- rebuild physicellpy before running it.

random.gauss()/random.random() are used instead of PhysiCell's own
NormalRandom()/UniformRandom() -- same statistics, just a different RNG
stream, which doesn't matter here since nothing in this script depends on
matching the C++ build's exact random sequence.
"""
import math
import random

# import physicellpy as pc


def setup_tissue(pc):
    Xmin, Ymin, Zmin, Xmax, Ymax, Zmax = pc.microenvironment.bounding_box

    if pc.simulate_2D():
        Zmin = 0.0
        Zmax = 0.0

    Xrange = Xmax - Xmin
    Yrange = Ymax - Ymin
    Zrange = Zmax - Zmin

    # --- create some of each type of cell (generic part) ---
    n_per_type = 0
    if pc.parameters.ints.find_index("number_of_cells") >= 0:
        n_per_type = pc.parameters.ints("number_of_cells")

    for cd_name in pc.cell_type_names():
        pCD = pc.find_cell_definition(cd_name)
        print(f"Placing cells of type {cd_name} ...")
        for _ in range(n_per_type):
            c = pc.create_cell(pCD)
            c.position = [
                Xmin + random.random() * Xrange,
                Ymin + random.random() * Yrange,
                Zmin + random.random() * Zrange,
            ]
    print()

    # --- custom placement: hex-packed tumor of "cancer cell" ---
    pCD = pc.find_cell_definition("cancer cell")
    cell_radius = pCD.phenotype.geometry.radius
    cell_spacing = 0.95 * 2.0 * cell_radius

    tumor_radius = pc.parameters.doubles("tumor_radius")

    p_mean = pc.parameters.doubles("oncoprotein_mean")
    p_sd = pc.parameters.doubles("oncoprotein_sd")
    p_min = pc.parameters.doubles("oncoprotein_min")
    p_max = pc.parameters.doubles("oncoprotein_max")

    def draw_oncoprotein():
        p = random.gauss(p_mean, p_sd)
        return min(max(p, p_min), p_max)

    def place(x, y):
        cell = pc.create_cell(pCD)
        cell.position = [x, y, 0.0]
        cell.custom_data["oncoprotein"] = draw_oncoprotein()

    y = 0.0
    n = 0
    while y < tumor_radius:
        x = 0.5 * cell_spacing if n % 2 == 1 else 0.0
        x_outer = math.sqrt(tumor_radius * tumor_radius - y * y)

        while x < x_outer:
            place(x, y)
            if abs(y) > 0.01:
                place(x, -y)
            if abs(x) > 0.01:
                place(-x, y)
                if abs(y) > 0.01:
                    place(-x, -y)
            x += cell_spacing

        y += cell_spacing * math.sqrt(3.0) / 2.0
        n += 1

    # --- oncoprotein summary statistics across all cells ---
    cells = pc.all_cells()
    values = [c.custom_data["oncoprotein"] for c in cells if "oncoprotein" in c.custom_data]
    if values:
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / max(len(values) - 1, 1)
        stdev = math.sqrt(variance)
        print()
        print("Oncoprotein summary:")
        print("===================")
        print(f"mean: {mean}")
        print(f"standard deviation: {stdev}")
        print(f"[min max]: [{min(values)} {max(values)}]")
        print()

    # --- load cells from your CSV file (if enabled) ---
    pc.load_cells_from_pugixml()

    return cells