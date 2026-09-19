physicellpy
============

pybind11 bindings for `PhysiCell <https://github.com/MathCancer/PhysiCell>`_,
a physics-based multicellular simulator. ``Cell``/``CellDefinition``/
``Phenotype`` and their sub-objects implement the behavior grammar described
in Johnson, Bergman, et al., "Human interpretable grammar encodes
multicellular systems biology models to democratize virtual cell
laboratories" (*Cell*, Volume 188) -- see ``doc/Cell_grammar_supp.pdf`` in the
source repository for the full reference-parameter tables cited throughout
this API reference.

.. toctree::
   :maxdepth: 2

   api
   publications
   funding

Getting started
----------------

.. code-block:: python

   import physicellpy as pc

   pc.initialize("config/PhysiCell_settings.xml")
   pc.setup_tissue()

   while pc.current_time() < pc.max_time():
       pc.run_simulation_step()
