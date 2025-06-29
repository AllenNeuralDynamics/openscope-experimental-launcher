Launcher Configuration Parameters
=================================

This page documents all configuration parameters available for the OpenScope Experimental Launcher and its interface-specific launchers (Bonsai, Python, MATLAB).

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

BonsaiLauncher Parameters
------------------------
- Inherits all BaseLauncher parameters.
- ``workflow_path``: Path to the Bonsai workflow file (.bonsai). Required.
- ``bonsai_executable``: Path to the Bonsai executable. Optional.
- ``bonsai_args``: List of additional arguments to pass to Bonsai. Optional.

PythonLauncher Parameters
------------------------
- Inherits all BaseLauncher parameters.
- ``script_path``: Path to the Python experiment script. Required.
- ``python_executable``: Path to the Python interpreter. Optional.
- ``python_args``: List of additional arguments to pass to Python. Optional.

MatlabLauncher Parameters
------------------------
- Inherits all BaseLauncher parameters.
- ``script_path``: Path to the MATLAB experiment script. Required.
- ``matlab_executable``: Path to the MATLAB executable. Optional.
- ``matlab_args``: List of additional arguments to pass to MATLAB. Optional.

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
    "bonsai_executable": "C:/Program Files/Bonsai/Bonsai.exe",
    "pre_acquisition_pipeline": ["example_pre_module"],
    "post_acquisition_pipeline": ["example_post_module"]
  }

Notes
-----
- All parameters are case-sensitive.
- Unused parameters are ignored by launchers that do not require them.
- For more details on resource monitoring, see :doc:`resource-monitoring`.
