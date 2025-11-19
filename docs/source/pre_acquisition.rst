Pre-Acquisition Modules
=======================

The full reference for pre-acquisition pipeline modules now lives in the :ref:`pre-modules` section of :doc:`modules`.

Quick Reminders
---------------

- Populate ``pre_acquisition_pipeline`` in your parameter file with module names under
  ``src/openscope_experimental_launcher/pre_acquisition``.
- Each module implements ``run_pre_acquisition`` (or ``run``) and should return ``0`` on success.
- Refer to :doc:`modules` for detailed parameter descriptions, built-in module catalogs, and extension tips.
