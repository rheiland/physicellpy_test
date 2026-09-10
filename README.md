# physicellpy_test

What OS/chip and version of Python are you using? Download an appropriate .whl and run `pip install <full-name>.whl` (or maybe pip installing from the URL?)

```
# inspect the package's contents:

$ python
...
>>> import physicellpy
>>> dir(physicellpy)
['BoolParameters', 'Cell', 'CellDefinition', 'CellIntegrity', 'CellInteractions', 'CellParameters', 'CellTransformations', 'CustomCellData', 'Death', 'DoubleParameters', 'Geometry', 'HypothesisRule', 'HypothesisRuleset', 'IntParameters', 'Mechanics', 'Microenvironment', 'Motility', 'Phenotype', 'PhysiMeSSCell', 'PhysiMeSSFibre', 'SVGOptions', 'Secretion', 'StringParameters', 'UserParameters', 'Volume', '__doc__', '__file__', '__loader__', '__name__', '__package__', '__spec__', 'add_rule', 'all_cells', 'cell_defaults', 'cell_type_names', 'clear_svg_coloring_function', 'config_folder', 'create_cell', 'current_time', 'delete_cell', 'diffusion_dt', 'fibre_cell_definitions', 'find_cell_definition', 'find_ruleset', 'get_single_behavior', 'get_single_signal', 'initialize', 'is_fibre', 'load_cells_from_pugixml', 'max_time', 'mechanics_dt', 'microenvironment', 'parameters', 'physimess_mechanics', 'read_rules', 'register_cell_definition', 'remove_physimess_out_of_bounds_fibres', 'run_simulation_step', 'save_multicellds', 'save_svg', 'save_svg_legend', 'set_behavior_base_value', 'set_behavior_max_value', 'set_behavior_min_value', 'set_behavior_parameters', 'set_hypothesis_parameters', 'set_single_behavior', 'set_svg_coloring_function', 'setup_physimess_cell_definition', 'setup_tissue', 'simulate_2D', 'svg_options', 'sync_cell_hooks', 'update_cell_and_death_parameters_O2_based']
>>> 
```

```
cd samples/heterogeneity
python hetero.py
```
