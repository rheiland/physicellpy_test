API reference
==============

Simulation setup and control
------------------------------

.. autofunction:: physicellpy.initialize
.. autofunction:: physicellpy.setup_tissue
.. autofunction:: physicellpy.run_simulation_step
.. autofunction:: physicellpy.sync_cell_hooks
.. autofunction:: physicellpy.current_time
.. autofunction:: physicellpy.max_time
.. autofunction:: physicellpy.diffusion_dt
.. autofunction:: physicellpy.mechanics_dt
.. autofunction:: physicellpy.simulate_2D
.. autofunction:: physicellpy.config_folder
.. autofunction:: physicellpy.load_cells_from_pugixml

.. autoclass:: physicellpy.UserParameters
   :members:

Cells and cell types
----------------------

.. autofunction:: physicellpy.create_cell
.. autofunction:: physicellpy.delete_cell
.. autofunction:: physicellpy.all_cells
.. autofunction:: physicellpy.find_cell_definition
.. autofunction:: physicellpy.cell_type_names
.. autofunction:: physicellpy.register_cell_definition

.. autoclass:: physicellpy.Cell
   :members:

.. autoclass:: physicellpy.CellDefinition
   :members:

.. autoclass:: physicellpy.CellParameters
   :members:

.. autoclass:: physicellpy.CustomCellData
   :members:

Phenotype and the behavior grammar
-------------------------------------

Field/method docstrings in this section cite the reference (or recommended)
parameter values from *Cell_grammar_supp.pdf*'s behavior dictionary tables
directly, so a docstring here doubles as a quick reference for reasonable
default magnitudes.

.. autoclass:: physicellpy.Phenotype
   :members:

.. autoclass:: physicellpy.Volume
   :members:

.. autoclass:: physicellpy.Geometry
   :members:

.. autoclass:: physicellpy.Mechanics
   :members:

.. autoclass:: physicellpy.Motility
   :members:

.. autoclass:: physicellpy.Death
   :members:

.. autoclass:: physicellpy.Secretion
   :members:

.. autoclass:: physicellpy.CellInteractions
   :members:

.. autoclass:: physicellpy.CellTransformations
   :members:

.. autoclass:: physicellpy.CellIntegrity
   :members:

Behavior rules (Hypothesis_Rule grammar)
-------------------------------------------

.. autofunction:: physicellpy.find_ruleset
.. autofunction:: physicellpy.read_rules
.. autofunction:: physicellpy.add_rule
.. autofunction:: physicellpy.set_hypothesis_parameters
.. autofunction:: physicellpy.set_behavior_parameters
.. autofunction:: physicellpy.set_behavior_base_value
.. autofunction:: physicellpy.set_behavior_min_value
.. autofunction:: physicellpy.set_behavior_max_value
.. autofunction:: physicellpy.get_single_signal
.. autofunction:: physicellpy.get_single_behavior
.. autofunction:: physicellpy.set_single_behavior
.. autofunction:: physicellpy.update_cell_and_death_parameters_O2_based

.. autoclass:: physicellpy.HypothesisRule
   :members:

.. autoclass:: physicellpy.HypothesisRuleset
   :members:

Microenvironment
-------------------

.. autoclass:: physicellpy.Microenvironment
   :members:

Output
--------

.. autofunction:: physicellpy.save_svg
.. autofunction:: physicellpy.save_svg_legend
.. autofunction:: physicellpy.save_multicellds
.. autofunction:: physicellpy.set_svg_coloring_function
.. autofunction:: physicellpy.clear_svg_coloring_function

.. autoclass:: physicellpy.SVGOptions
   :members:

PhysiMeSS (fibre agents)
---------------------------

.. autofunction:: physicellpy.setup_physimess_cell_definition
.. autofunction:: physicellpy.is_fibre
.. autofunction:: physicellpy.fibre_cell_definitions
.. autofunction:: physicellpy.physimess_mechanics
.. autofunction:: physicellpy.remove_physimess_out_of_bounds_fibres

.. autoclass:: physicellpy.PhysiMeSSFibre
   :members:

.. autoclass:: physicellpy.PhysiMeSSCell
   :members:
