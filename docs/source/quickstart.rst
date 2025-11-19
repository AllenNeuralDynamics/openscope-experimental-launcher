Quick Start Guide
=================

Minimal steps to launch an experiment with the OpenScope Experimental Launcher.

Configuration Layers
--------------------

1. **Rig Config (TOML)** – static hardware + defaults.
2. **Parameter File (JSON)** – experiment-specific settings.
3. **Runtime Prompts** – fill / override missing required fields interactively.

Precedence: Runtime Prompts > Parameter File > Rig Config.

Example Minimal Parameter File
------------------------------

.. code-block:: json
   :caption: example_params.json

   {
     "subject_id": "mouse_001",
     "user_id": "operator",
     "script_path": "C:/local/scripts/task.py",
     "output_root_folder": "D:/OpenScopeData"
   }

Run the Launcher
----------------

.. code-block:: bash

   python run_launcher.py --param_file params/example_minimalist_params.json

Placeholders
------------

Use rig config values inside ``script_parameters`` via:

``{rig_param:COM_port}`` → replaced at initialization.

Pipeline Modules
----------------

Add ordered module names to your parameter file:

.. code-block:: json

   {
     "pre_acquisition_pipeline": ["mouse_weight_pre_prompt"],
     "post_acquisition_pipeline": ["session_creator"]
   }

Notes Workflow Example
----------------------

The repository ships with ``params/experiment_notes_pipeline.json`` which demonstrates the paired notes modules:

.. code-block:: json

    {
       "pre_acquisition_pipeline": ["experiment_notes_editor"],
       "post_acquisition_pipeline": ["experiment_notes_finalize"],
       "experiment_notes_launch_editor": true,
       "experiment_notes_filename": "notes/experiment_notes.txt"
    }

When launched, the editor creates the notes file under the session folder (via ``{session_folder}`` expansion) and opens Notepad so the operator can start typing immediately. The post step pauses at the end of the session until the operator confirms the notes are saved.

Outputs
-------

Session folder will contain ``launcher_metadata/`` with:

* processed_parameters.json
* end_state.json (flattened)
* debug_state.json (if crash)

Post-acquisition ``session_creator`` can build ``session.json`` later.

Next Steps
----------

* See :doc:`parameter_files` for full schema.
* See :doc:`rig_config` for rig TOML details.
* See :doc:`end_state_system` for metadata formats.