Launcher Configuration Parameters
=================================

This page documents all configuration parameters available for the OpenScope Experimental Launcher. A single ``BaseLauncher`` handles orchestration; interface adapters (Bonsai / MATLAB / Python / Custom) provide only subprocess spawning.

BaseLauncher Parameters
----------------------
These parameters control the core behavior of the launcher and are accepted in the main parameter JSON file.

+---------------------------+-----------+---------------------------------------------------------------------+
| Parameter                 | Type      | Description                                                         |
+===========================+===========+=====================================================================+
| subject_id                | string    | Animal or experiment subject ID. Required.                          |
+---------------------------+-----------+---------------------------------------------------------------------+
| user_id                   | string    | Experimenter user ID. Required.                                     |
+---------------------------+-----------+---------------------------------------------------------------------+
| output_root_folder        | string    | Root directory for output session folders. Defaults to cwd.         |
+---------------------------+-----------+---------------------------------------------------------------------+
+---------------------------+-----------+---------------------------------------------------------------------+
| resource_log_interval     | int/float | Interval (seconds) between resource log entries. Optional.          |
+---------------------------+-----------+---------------------------------------------------------------------+
| centralized_log_directory | string    | If set, copies logs to this directory for centralized storage.      |
+---------------------------+-----------+---------------------------------------------------------------------+
| pre_acquisition_pipeline  | list      | List of pre-acquisition module names to run before experiment.      |
+---------------------------+-----------+---------------------------------------------------------------------+
| post_acquisition_pipeline | list      | List of post-acquisition module names to run after experiment.      |
+---------------------------+-----------+---------------------------------------------------------------------+
| script_path               | string    | Path to the experiment script (for Python/Matlab launchers).        |
+---------------------------+-----------+---------------------------------------------------------------------+
| rig_config_path           | string    | Path to the rig configuration TOML file. Optional.                  |
+---------------------------+-----------+---------------------------------------------------------------------+
| repository_url            | string    | URL of the experiment code repository to clone/use. Optional.       |
+---------------------------+-----------+---------------------------------------------------------------------+
| repository_commit_hash    | string    | Commit hash or branch to checkout (default: 'main'). Optional.      |
+---------------------------+-----------+---------------------------------------------------------------------+
| local_repository_path     | string    | Local directory to clone/use the repository. Optional.              |
+---------------------------+-----------+---------------------------------------------------------------------+

Optional Interface Parameters
-----------------------------
The following keys apply only when launching a specific external environment.
Include only those you need; unused keys are ignored.

Bonsai
~~~~~~

* ``workflow_path`` – path to the ``.bonsai`` workflow file.
* ``bonsai_executable`` – override Bonsai executable path.
* ``bonsai_args`` – additional CLI arguments passed to Bonsai.

Python
~~~~~~

* ``python_executable`` – interpreter path override.
* ``python_args`` – extra CLI arguments supplied before the script path.

MATLAB (Shared Engine)
~~~~~~~~~~~~~~~~~~~~~~

* ``matlab_engine_name`` – shared engine name (default
  ``"openscope_launcher"``).
* ``matlab_entrypoint`` / ``matlab_function`` – MATLAB function to call.
* ``matlab_entrypoint_args`` – positional arguments forwarded to MATLAB.
* ``matlab_entrypoint_kwargs`` – dictionary of name/value pairs appended to
  the argument list.
* ``matlab_entrypoint_nargout`` – number of expected outputs (default ``0``).
* ``matlab_pass_session_folder`` – include the session folder in the argument
  list (default ``true``).
* ``matlab_session_folder_position`` – insertion position for the session
  folder (``"prepend"``/``"append"``/``"ignore"`` or integer index).
* ``matlab_enable_resume`` – enable automatic resume attempts when the engine
  drops (default ``true``).
* ``matlab_resume_keyword`` – keyword used when appending the resume flag.
* ``matlab_engine_connect_timeout_sec`` – timeout waiting for the engine to
  appear (seconds).
* ``matlab_engine_connect_poll_interval_sec`` – polling interval during
  engine connection attempts (seconds).
* ``matlab_cancel_timeout_sec`` – timeout waiting for MATLAB to acknowledge a
  cancellation request (seconds).
* ``matlab_keep_engine_alive`` – leave the engine running after the launcher
  finishes (default ``true``).

.. note::
  These interface parameters are optional and may be superseded by a custom
  ``_create_process`` implementation in a subclass or adapter.

Example Parameter File
---------------------
::

  {
    "subject_id": "mouse123",
    "user_id": "experimenter1",
    "output_root_folder": "D:/OpenScopeData",
    "resource_log_interval": 5,
    "workflow_path": "C:/Workflows/my_experiment.bonsai",
    "pre_acquisition_pipeline": ["mouse_weight_pre_prompt"],
    "post_acquisition_pipeline": ["experiment_notes_post_prompt"]
  }

Notes
-----
- All parameters are case-sensitive.
- Unused optional interface parameters are ignored.
- Use placeholders (``{rig_param:<key>}``) inside values to inject rig configuration.
- For more details on resource monitoring, see :doc:`resource-monitoring`.
