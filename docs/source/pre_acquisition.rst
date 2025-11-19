Pre-Acquisition System
======================

The pre-acquisition system allows you to run one or more modular steps before the main experiment starts. This is useful for hardware checks, inter-launcher communication, parameter validation, or any setup required before data acquisition.

Philosophy
----------
- All pre-acquisition logic is handled by standalone modules, not the launcher core.
- Modules are inserted via the `pre_acquisition_pipeline` list in your parameter file.
- Each module is focused, testable, and reusable.

How It Works
------------
- Add a `pre_acquisition_pipeline` list to your parameter JSON file. Each entry is the name of a Python module in `src/openscope_experimental_launcher/pre_acquisition/`.
- Each module must expose a callable entry point (``run_pre_acquisition`` is recommended) and return 0 for success, 1 for failure.
- The launcher will import and run each module in order before starting the experiment. If any step fails (returns 1 or raises), the experiment will not start.

Available Pre-Acquisition Modules
---------------------------------
- **experiment_notes_editor**: Creates an experiment-notes file in the session directory and optionally launches a text editor (Notepad by default) so notes can be captured throughout the run. Designed to pair with the ``experiment_notes_finalize`` post-acquisition module.
- **mouse_weight_pre_prompt**: Prompts for and records the mouse's weight before the experiment.
- **example_pre_acquisition_module**: Template for creating new pre-acquisition modules.

Example Parameter File
----------------------
.. code-block:: json

    {
        "launcher": "base",
        "pre_acquisition_pipeline": [
            "experiment_notes_editor",
            "mouse_weight_pre_prompt"
        ],
        ...
    }

Custom Parameters
-----------------
Modules can read custom parameters from the param file (e.g., numeric thresholds, wait times specific to your module). Define and document any new keys your module expects inside its docstring.

Best Practices
--------------
- Keep each module focused on a single task.
- Log all actions for traceability.
- Use exceptions or return 1 to signal failure and prevent the experiment from starting.

See also: `src/openscope_experimental_launcher/pre_acquisition/` for example modules.
