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

Session Synchronization Parameters
----------------------------------
``BaseLauncher`` can negotiate a shared session folder name across multiple launchers (for example,
behavior + imaging rigs) before any data is written. Configure the following keys in the main
parameter JSON file to enable the built-in TCP handshake:

- ``session_sync_role``: ``"master"`` or ``"slave"`` (any other value disables the feature).
- ``session_sync_port``: TCP port used by both master and slave launchers.
- ``session_sync_expected_slaves`` (master): number of slave launchers that must acknowledge before
  the master proceeds.
- ``session_sync_bind_host`` (master): interface to bind the listening socket to (``127.0.0.1`` for
  same-machine tests, ``0.0.0.0`` for remote clients).
- ``session_sync_master_host`` (slave): hostname or IP address of the master.
- ``session_sync_node_name`` (optional): friendly label displayed in logs for each launcher.
- ``session_sync_key_param`` (optional): parameter that carries the shared key (defaults to
  ``subject_id``). Override via ``session_sync_session_key`` when necessary.
- ``session_sync_session_name`` (optional, master): explicit folder name. If omitted, the master
  falls back to ``session_sync_name_param`` (defaults to ``session_uuid``) or the automatically
  generated timestamp-based value.

Example snippet:

.. code-block:: json

   {
     "subject_id": "mouse123",
     "user_id": "tester",
     "session_sync_role": "master",
     "session_sync_port": 47001,
     "session_sync_expected_slaves": 2
   }

Workflow checklist:

1. Pick a TCP port that is free on the master machine and set ``session_sync_port`` to that value in
   every launcher.
2. Launch the master parameter file first (``session_sync_role = "master"``). ``BaseLauncher`` logs
   that it is listening and blocks until the expected number of slaves connect.
3. Start each slave (``session_sync_role = "slave"``) with ``session_sync_master_host`` pointing to
   the master's hostname/IP. Slaves retry connections until the master responds, then adopt the
   shared session name announced by the master.
4. Once all acknowledgements are received, every launcher resumes its normal workflow (repository
   setup, folder creation, logging, etc.) with a synchronized ``session_uuid``.

Timeout and retry controls:

- ``session_sync_timeout_sec``: maximum time the master waits for all slaves _or_ a slave waits to
  reach the master (default 120 seconds).
- ``session_sync_ack_timeout_sec``: per-message timeout during the JSON handshake (default 30
  seconds).
- ``session_sync_retry_delay_sec`` (slave only): delay between connection attempts (default 1
  second).

Local testing: bind the master to ``127.0.0.1`` and set each slave's ``session_sync_master_host`` to
``127.0.0.1``. The repository includes ready-to-run examples in
``params/session_sync_master_example.json`` and ``params/session_sync_slave_example.json``.

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
  ``"slap2_launcher"``).
* ``matlab_entrypoint`` / ``matlab_function`` – MATLAB function to call
  (defaults to ``"slap2_launcher"`` so it can be omitted).
* ``matlab_entrypoint_args`` – optional positional overrides; SLAP2 launches
  can omit this because the Python launcher automatically issues
  ``slap2_launcher('execute', ...)``.
* ``script_parameters`` – optional dictionary of name/value pairs appended to
  the MATLAB argument list (recommended place to pass rig paths).
* ``matlab_entrypoint_kwargs`` – dictionary of name/value pairs appended after
  ``script_parameters`` when additional overrides are required.
* ``matlab_entrypoint_nargout`` – number of expected outputs (default ``0``).
* ``matlab_engine_connect_timeout_sec`` – timeout waiting for the engine to
  appear (seconds).
* ``matlab_engine_connect_poll_interval_sec`` – polling interval during
  engine connection attempts (seconds).
* ``matlab_cancel_timeout_sec`` – timeout waiting for MATLAB to acknowledge a
  cancellation request (seconds).
* ``matlab_keep_engine_alive`` – leave the engine running after the launcher
  finishes (default ``true``).

Session folder injection and resume signalling happen automatically. Legacy
keys such as ``matlab_pass_session_folder``, ``matlab_session_folder_position``,
``matlab_enable_resume``, and ``matlab_resume_keyword`` remain supported for
backward compatibility but should be omitted from new files.

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
