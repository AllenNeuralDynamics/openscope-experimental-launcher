.. _post_acquisition:

Post-Acquisition Tools
======================

The OpenScope Experimental Launcher includes a modular post-acquisition system designed to handle data transformation and session creation after experiment completion.

Philosophy
----------

- All post-acquisition logic is handled by standalone modules, not the launcher core.
- Modules are inserted via the ``post_acquisition_pipeline`` list in your parameter file.
- Each module is focused, testable, and reusable.

How It Works
------------

- Add a ``post_acquisition_pipeline`` list to your parameter JSON file. Each entry is the name of a Python module in ``src/openscope_experimental_launcher/post_acquisition/``.
- Each module must define a function ``main(param_file)`` and return 0 for success, 1 for failure.
- The launcher will import and run each module in order after the experiment completes. If any step fails (returns 1 or raises), the pipeline stops and logs the error.

Available Post-Acquisition Modules
----------------------------------

- **session_creator**: Creates standardized ``session.json`` files from experiment data using the AIND data schema.
- **stimulus_table_predictive_processing**: Converts Predictive Processing stimulus tables to a standardized format for downstream analysis.
- **session_enhancer_bonsai**: Adds Bonsai-specific metadata and enrichment to session files.
- **session_enhancer_predictive_processing**: Adds Predictive Processing-specific metadata and enrichment to session files.
- **session_enhancer_slap2**: Adds SLAP2-specific metadata and enrichment to session files.
- **mouse_weight_post_prompt**: Prompts for and records the mouse's weight after the experiment.
- **experiment_notes_post_prompt**: Prompts for and records experiment notes after the experiment.
- **example_post_acquisition_module**: Template for creating new post-acquisition modules.

Example Parameter File
----------------------

.. code-block:: json

    {
        "launcher": "base",
        "post_acquisition_pipeline": [
            "session_creator",
            "mouse_weight_post_prompt",
            "experiment_notes_post_prompt"
        ],
        ...
    }

Best Practices
--------------

- Keep each module focused on a single task.
- Log all actions for traceability.
- Use exceptions or return 1 to signal failure and stop the pipeline.

See also: ``src/openscope_experimental_launcher/post_acquisition/`` for example modules.
