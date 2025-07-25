Launchers
=========

The OpenScope Experimental Launcher provides a modular architecture with specialized launchers for different experimental environments. Each launcher is built on a common base and handles specific interfaces (Bonsai, MATLAB, Python) with process management and monitoring.

Modular Architecture Benefits
-----------------------------

**Separation of Concerns:**

- Launchers handle process management and monitoring
- Interfaces handle process creation
- Utilities provide shared functionality
- **All session file creation and post-acquisition logic are handled by modular pipeline modules, not the launcher core.**

**Flexibility:**

- Easy to add new interfaces (e.g., LabVIEW, Julia)
- Stateless interfaces for better testing

**Maintainability:**

- Clear separation between launcher logic and interface logic
- Easier to extend and modify individual components
- Better code reusability


Base Launcher
-------------

The foundation for all other launchers, providing core process management and session tracking.

.. code-block:: python

   from openscope_experimental_launcher.launchers import BaseLauncher

   launcher = BaseLauncher()
   success = launcher.run("parameters.json")

**Features:**

- Universal process management with monitoring
- Session UUID generation and tracking
- Memory and resource monitoring
- Standardized parameter validation

**Output:**

- Standardized logging and monitoring data

Bonsai Launcher
---------------

Specialized launcher for Bonsai visual programming workflows.

.. code-block:: python

   from openscope_experimental_launcher.launchers import BonsaiLauncher

   launcher = BonsaiLauncher()
   success = launcher.run("bonsai_params.json")

**Enhanced Features:**

- Git repository management and workflow checkout
- Windows job objects for robust process control
- Bonsai-specific parameter validation
- Workflow path resolution and validation

**Required Parameters:**

.. code-block:: json   {
       "repository_url": "https://github.com/user/workflow.git",
       "script_path": "path/to/workflow.bonsai",
       "output_root_folder": "C:/experiment_data"
   }

MATLAB Launcher
---------------

Specialized launcher for MATLAB-based experiments.

.. code-block:: python

   from openscope_experimental_launcher.launchers import MATLABLauncher

   launcher = MATLABLauncher()
   success = launcher.run("matlab_params.json")

**Required Parameters:**

.. code-block:: json   {
       "script_path": "path/to/script.m",
       "output_root_folder": "C:/experiment_data"
   }

Python Launcher
---------------

Specialized launcher for Python-based experiments.

.. code-block:: python

   from openscope_experimental_launcher.launchers import PythonLauncher

   launcher = PythonLauncher()
   success = launcher.run("python_params.json")


**Required Parameters:**

.. code-block:: json   {
       "script_path": "path/to/script.py",
       "output_root_folder": "C:/experiment_data"
   }

Launcher Interfaces
-------------------

Each launcher uses a corresponding stateless interface module that provides the process creation logic:

- ``BonsaiInterface``: Creates Bonsai workflow processes
- ``MATLABInterface``: Creates MATLAB script processes  
- ``PythonInterface``: Creates Python script processes

These interfaces can be used independently for custom launcher implementations:

.. code-block:: python

   from openscope_experimental_launcher.interfaces import BonsaiInterface
   from openscope_experimental_launcher.launchers import BaseLauncher

   # Direct interface usage
   process = BonsaiInterface.create_process(
       bonsai_path="path/to/workflow.bonsai",
       parameters={"param1": "value1"}
   )

   # Custom launcher with interface
   class CustomLauncher(BaseLauncher):
       def _create_process(self, script_path, parameters):
           return BonsaiInterface.create_process(script_path, parameters)


Custom Launcher Development
---------------------------

Create custom launchers by extending BaseLauncher:

.. code-block:: python

   from openscope_experimental_launcher.launchers import BaseLauncher

   class CustomLauncher(BaseLauncher):
       """Custom launcher for specialized experiments."""
       
       def _create_process(self, script_path, parameters):
           """Create process for custom interface."""
           command = ["custom_tool", script_path]
           
           # Add parameters as command line arguments
           for key, value in parameters.items():
               command.extend([f"--{key}", str(value)])
           
           return subprocess.Popen(
               command,
               stdout=subprocess.PIPE,
               stderr=subprocess.PIPE,
               text=True
           )

**Custom Launcher Guidelines:**

- Always extend ``BaseLauncher``
- Implement ``_create_process()`` method
- Return a ``subprocess.Popen`` object
- Handle parameters appropriately for your interface
- Add interface-specific validation as needed
