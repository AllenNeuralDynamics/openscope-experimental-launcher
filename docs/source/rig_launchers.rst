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

