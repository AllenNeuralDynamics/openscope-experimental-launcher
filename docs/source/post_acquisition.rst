Post-Acquisition Modules
========================

The detailed reference for post-acquisition pipeline modules is consolidated in the :ref:`post-modules` section of :doc:`modules`.

Quick Reminders
---------------

- Populate ``post_acquisition_pipeline`` with module names from
  ``src/openscope_experimental_launcher/post_acquisition``.
- Modules typically expose ``run_post_acquisition`` (or ``run``) and should return ``0`` on success.
- See :doc:`modules` for descriptions, parameter tables, and best practices covering all built-in modules.
