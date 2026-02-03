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

    launcher = BaseLauncher(param_file="parameters.json")
    success = launcher.run()

Interface Adapters
------------------

Adapters encapsulate only process spawning. Example adapter-based customization for a workflow system:

.. code-block:: python

   from openscope_experimental_launcher.launchers import BaseLauncher
   from openscope_experimental_launcher.interfaces import bonsai_interface

   class WorkflowLauncher(BaseLauncher):
       def create_process(self):
           workflow_path = self.params["script_path"]
           bonsai_exe_path = self.params["bonsai_exe_path"]
           args = bonsai_interface.construct_workflow_arguments(self.params)
           return bonsai_interface.start_workflow(
               workflow_path=workflow_path,
               bonsai_exe_path=bonsai_exe_path,
               arguments=args,
               output_folder=self.output_session_folder,
           )

   success = WorkflowLauncher(param_file="workflow_params.json").run()

MATLAB Shared Engine Adapter
----------------------------

The MATLAB launcher connects to a *shared* MATLAB Engine session rather than
starting ``matlab.exe`` directly. This enables operator-controlled resume
flows:

* In MATLAB, call ``slap2_launcher('slap2_launcher')`` (or your preferred
    ``matlab_engine_name``) to share the engine and display the OpenScope UI.
* Python connects using the parameters described in
    :doc:`matlab_launcher`, invokes the configured entry point (defaulting to
    ``slap2_launcher``) by issuing ``slap2_launcher('execute', ...)`` which in
    turn always calls the shipped ``slap2`` acquisition function. The Python
    side also injects the session folder when configured.
* If the engine disconnects mid-run, the launcher attempts to reconnect and
    resumes only after the operator confirms via the MATLAB UI. When no Python
    launcher is attached, selecting a rig description and session folder inside
    the UI automatically enables **Start SLAP2 acquisition**, allowing fully
    manual runs that still log metadata and copy rig files into the session
    folder.

Regardless of where the previous attempt stopped, every resume requires the
operator to press **Start/Resume SLAP2 acquisition** again before signaling
completion. This forces SLAP2 to relaunch, reinitialize microscope hardware,
and only then allows the **End SLAP2 acquisition** confirmation that releases
Python to continue.

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
       def create_process(self):
           script_path = self.params["script_path"]
           parameters = self.params.get("script_parameters", {})
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

