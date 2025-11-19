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
- **experiment_notes_editor**: Creates an experiment-notes file in the session directory and can launch a text editor (Notepad by default) so notes stay open during acquisition. Designed to pair with the ``experiment_notes_finalize`` post-acquisition module.
- **mouse_weight_pre_prompt**: Prompts for and records the mouse's weight before the experiment.
- **example_pre_acquisition_module**: Template for creating new pre-acquisition modules.

Experiment Notes Editor Parameters
----------------------------------
The notes editor module respects the same placeholder expansion as the launcher, so you can reference ``{session_folder}`` to keep files scoped to the active run. Common parameters include:

- ``experiment_notes_filename`` (default ``"experiment_notes.txt"``): relative paths are resolved under the session directory after placeholder expansion. Example: ``"notes/experiment_notes.txt"``.
- ``experiment_notes_launch_editor`` (default ``true``): disable if you only need the file pre-created.
- ``experiment_notes_editor_command`` (default ``"notepad.exe"``) and ``experiment_notes_editor_args``: override to launch your preferred editor.
- ``experiment_notes_encoding`` (default ``"utf-8"``): encoding used when creating the initial notes file.

The module writes a simple header with a UTC timestamp the first time the notes file is created. Subsequent runs reuse the existing file.

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
