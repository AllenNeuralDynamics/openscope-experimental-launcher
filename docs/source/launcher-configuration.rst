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
| resource_log_enabled      | bool      | If ``true``, enables resource usage monitoring. Default: off.       |
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

Optional Interface-Specific Parameters
-------------------------------------
The following keys apply only when launching a specific external environment. Include only those you need; unused keys are ignored.

+----------------------+-----------+-----------------------------------------------+
| Parameter            | Type      | Applies To / Description                      |
+======================+===========+===============================================+
| workflow_path        | string    | Bonsai: path to ``.bonsai`` workflow file.    |
+----------------------+-----------+-----------------------------------------------+
| bonsai_executable    | string    | Bonsai: override Bonsai executable path.      |
+----------------------+-----------+-----------------------------------------------+
| bonsai_args          | list      | Bonsai: extra CLI args.                       |
+----------------------+-----------+-----------------------------------------------+
| python_executable    | string    | Python: interpreter path override.            |
+----------------------+-----------+-----------------------------------------------+
| python_args          | list      | Python: extra CLI args.                       |
+----------------------+-----------+-----------------------------------------------+
| matlab_executable    | string    | MATLAB: executable path override.             |
+----------------------+-----------+-----------------------------------------------+
| matlab_args          | list      | MATLAB: extra CLI args.                       |
+----------------------+-----------+-----------------------------------------------+

.. note::
  These interface parameters are optional and may be superseded by a custom ``_create_process`` implementation in a subclass or adapter.

Example Parameter File
---------------------
::

  {
    "subject_id": "mouse123",
    "user_id": "experimenter1",
    "output_root_folder": "D:/OpenScopeData",
    "resource_log_enabled": true,
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
