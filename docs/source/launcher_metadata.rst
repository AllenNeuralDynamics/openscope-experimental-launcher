Launcher Metadata Folder
========================

Overview
--------

Each experiment session creates a ``launcher_metadata`` directory inside the session output folder containing small, machine-readable JSON files for downstream tools.

Current File Set
----------------

* **processed_parameters.json** – final merged parameters (rig config + param file + runtime prompts).
* **end_state.json** – flattened final state (no nested ``session_info``) with core identifiers.
* **debug_state.json** – only on crash; contains ``crash_info`` + ``launcher_state`` snapshot.

The design uses a minimal, flattened set of files for clarity and easy parsing.

Structure Example
-----------------

.. code-block:: text

  output_session_folder/
  ├── experiment.log
  ├── session.json            # Generated post-acquisition (optional)
  ├── launcher_metadata/
  │   ├── processed_parameters.json
  │   ├── end_state.json
  │   └── debug_state.json    # Only present if a crash occurred
  └── ... other data files

Creation Timeline
-----------------

1. At initialization: ``processed_parameters.json`` written after merges & prompts.
2. On normal completion: ``end_state.json`` saved.
3. On unexpected exception: ``debug_state.json`` written before shutdown.

Best Practices
--------------

* Treat files as immutable audit artifacts; do not edit manually.
* Use ``processed_parameters.json`` as the canonical input for post-acquisition tools.
* Treat ``end_state.json`` as a stable artifact.


Downstream Consumption
----------------------

The ``session_creator`` tool consumes both ``processed_parameters.json`` and ``end_state.json``. Missing optional fields are handled gracefully with warnings.

Reference Implementation
------------------------

See ``BaseLauncher.save_end_state`` and ``BaseLauncher.save_debug_state`` in ``src/openscope_experimental_launcher/launchers/base_launcher.py``.
