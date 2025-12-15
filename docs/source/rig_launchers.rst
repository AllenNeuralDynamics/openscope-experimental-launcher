Launchers
=========

The experimental flow is orchestrated by a single ``BaseLauncher``. External environments (Bonsai, MATLAB, Python, custom tools) are integrated via lightweight interface adapters or a custom ``_create_process`` override.

Overview
--------

``BaseLauncher`` responsibilities:

- Load + merge parameter file and rig configuration (with placeholders ``{rig_param:<key>}``)
- Prompt for missing required values
- Run ordered pre-acquisition pipeline modules
- Spawn acquisition subprocess
- Run ordered post-acquisition pipeline modules
- Write flattened metadata (``end_state.json``, ``debug_state.json``) and logs
- Optional resource monitoring and centralized log copying

Quick Start
-----------

.. code-block:: python

   from openscope_experimental_launcher.launchers import BaseLauncher

   launcher = BaseLauncher()
   launcher.run("parameters.json")

Interface Adapters
------------------

Adapters encapsulate only process spawning. Example adapter-based customization for a workflow system:

.. code-block:: python

   from openscope_experimental_launcher.launchers import BaseLauncher
   from openscope_experimental_launcher.interfaces import BonsaiInterface

   class WorkflowLauncher(BaseLauncher):
       def _create_process(self, script_path, parameters):
           return BonsaiInterface.create_process(bonsai_path=script_path, parameters=parameters)

   WorkflowLauncher().run("workflow_params.json")

MATLAB Shared Engine Adapter
----------------------------

The MATLAB launcher connects to a *shared* MATLAB Engine session rather than
starting ``matlab.exe`` directly. This enables operator-controlled resume
flows:

* In MATLAB, call ``slap2_launcher('slap2_launcher')`` (or your preferred
    ``matlab_engine_name``) to share the engine and display the OpenScope UI.
* Python connects using the parameters described in
    :doc:`matlab_launcher`, forwards ``matlab_entrypoint_args`` and injects the
    session folder when configured.
* If the engine disconnects mid-run, the launcher attempts to reconnect and
    resumes only after the operator confirms via the MATLAB UI.

For quick smoke testing, ``params/matlab_local_test_params.json`` exercises
the workflow with ``sample_matlab_entrypoint.m`` which writes a heartbeat file
to the session directory.

Custom Process Creation
-----------------------

Direct implementation using ``subprocess.Popen``:

.. code-block:: python

   import subprocess
   from openscope_experimental_launcher.launchers import BaseLauncher

   class CustomToolLauncher(BaseLauncher):
       def _create_process(self, script_path, parameters):
           cmd = ["custom_tool", script_path]
           for k, v in parameters.items():
               cmd.extend([f"--{k}", str(v)])
           return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

Guidelines
----------

- Extend only ``BaseLauncher`` (no parallel subclass hierarchy)
- Keep adapters stateless; they should just build and return a process object
- Return a ``subprocess.Popen`` instance
- Validate only parameters you actually use
- Leverage rig placeholders to avoid hard-coding machine-specific paths

