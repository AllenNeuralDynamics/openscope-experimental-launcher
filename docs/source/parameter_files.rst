Parameter Files
===============

JSON parameter files define experiment-specific configuration merged with rig config and runtime prompts.

Core Keys
---------

``script_path`` (required)
   Path to executable / script (Python, MATLAB, Bonsai, etc.).

``output_root_folder`` (optional)
   Base folder for session output; if omitted uses rig config default.

``subject_id`` / ``user_id`` (optional)
   Prompted if missing.

``pre_acquisition_pipeline`` / ``post_acquisition_pipeline`` (optional)
   Ordered pipeline definitions. Entries can be simple launcher-module names or structured objects containing
   ``module_type``, ``module_path``, and ``module_parameters``. See :ref:`Pipeline Entry Schema <pipeline-entry-schema>`
   in :doc:`modules` for details.

Placeholders
------------

Inject rig config values into ``script_parameters``:

``{rig_param:COM_port}``

Basic Example
-------------

.. code-block:: json

    {
       "subject_id": "mouse_001",
       "user_id": "operator",
       "script_path": "C:/tasks/run_task.py",
       "output_root_folder": "D:/OpenScopeData",
       "script_parameters": {
          "PortName": "{rig_param:COM_port}",
          "RecordCameras": "{rig_param:RecordCameras}"
       },
       "pre_acquisition_pipeline": ["mouse_weight_pre_prompt"],
       "post_acquisition_pipeline": ["session_creator"]
    }

MATLAB Shared Engine Example
----------------------------

The launcher connects to an already shared MATLAB Engine session. A minimal
parameter file looks like:

.. code-block:: json
    :caption: params/matlab_local_test_params.json

    {
       "launcher": "matlab",
       "subject_id": "test_mouse_local",
       "user_id": "local_operator",
       "output_root_folder": "C:/OpenScopeLocalSessions",
       "matlab_engine_name": "openscope_launcher",
       "matlab_entrypoint": "aind_launcher",
       "matlab_entrypoint_args": [
          "execute",
          "sample_matlab_entrypoint"
       ],
       "matlab_pass_session_folder": true,
       "matlab_enable_resume": true
    }

Before launching, start MATLAB, add the launchers directory to the path, and
share the engine:

.. code-block:: matlab

    addpath('C:/BonsaiDataPredictiveProcessing/openscope-experimental-launcher/src/openscope_experimental_launcher/launchers')
    aind_launcher('openscope_launcher')

Git Repository Support (Optional)
---------------------------------

``repository_url`` / ``repository_commit_hash`` / ``local_repository_path`` allow cloning & pinning code; omitted for purely local workflows.

Runtime Data Collection (Optional)
----------------------------------

``collect_mouse_runtime_data``: boolean enabling weight prompts.
``protocol_id``: list of identifiers.
``mouse_platform_name`` / ``active_mouse_platform``: platform metadata.

Script Parameters
-----------------

Arbitrary key-value pairs passed to the underlying process. Booleans preserved; launcher performs placeholder expansion before invocation.

Session Output
--------------

Launcher creates a timestamped session folder under ``output_root_folder`` containing a ``launcher_metadata`` directory with:

* processed_parameters.json
* end_state.json
* debug_state.json (only if crash)

Post-acquisition tools (e.g. ``session_creator``) derive ``session.json`` from these.

Reference
---------

See ``BaseLauncher._expand_rig_param_placeholders`` and ``BaseLauncher.save_end_state`` for implementation details.