API Reference - Launchers Module
===================================

The launchers module provides the main launcher classes for running experiments across different interfaces.

Base Launcher
-------------

.. autoclass:: openscope_experimental_launcher.launchers.base_launcher.BaseLauncher
   :members:
   :undoc-members:
   :show-inheritance:

   The foundational launcher class that provides core process management, session tracking, and monitoring functionality.

   **Key Methods:**

   .. automethod:: run
   .. automethod:: _create_process
   .. automethod:: _monitor_process
   .. automethod:: stop

   **Properties:**

   .. autoattribute:: session_uuid
   .. autoattribute:: start_time
   .. autoattribute:: stop_time
   .. autoattribute:: session_pkl_path

Bonsai Launcher
---------------

.. autoclass:: openscope_experimental_launcher.launchers.bonsai_launcher.BonsaiLauncher
   :members:
   :undoc-members:
   :show-inheritance:

   Specialized launcher for Bonsai visual programming workflows with Git repository management.

   **Enhanced Features:**
   
   - Git repository cloning and management
   - Bonsai workflow execution
   - Windows job object process control
   - Workflow parameter validation

MATLAB Launcher
---------------

.. autoclass:: openscope_experimental_launcher.launchers.matlab_launcher.MATLABLauncher
   :members:
   :undoc-members:
   :show-inheritance:

   Specialized launcher for MATLAB script execution with engine integration.

   **Enhanced Features:**
   
   - MATLAB engine integration
   - Script path validation
   - GPU configuration support
   - Cross-platform MATLAB execution

Python Launcher
---------------

.. autoclass:: openscope_experimental_launcher.launchers.python_launcher.PythonLauncher
   :members:
   :undoc-members:
   :show-inheritance:

   Specialized launcher for Python script execution with environment management.

   **Enhanced Features:**
   
   - Python environment management
   - Package dependency handling
   - Script execution with isolation
   - Real-time output capture

Example Usage
-------------

Basic Launcher Usage
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.launchers import BonsaiLauncher

   # Create and run a Bonsai experiment
   launcher = BonsaiLauncher()
   success = launcher.run("parameters.json")

   if success:
       print(f"Session UUID: {launcher.session_uuid}")
       print(f"Session data: {launcher.session_pkl_path}")

Custom Launcher Implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.launchers import BaseLauncher
   import subprocess

   class CustomLauncher(BaseLauncher):
       """Custom launcher for specialized tools."""
       
       def _create_process(self, script_path, parameters):
           """Create process for custom interface."""
           command = ["custom_tool", script_path]
           
           # Add parameters as arguments
           for key, value in parameters.items():
               command.extend([f"--{key}", str(value)])
           
           return subprocess.Popen(
               command,
               stdout=subprocess.PIPE,
               stderr=subprocess.PIPE,
               text=True
           )

Launcher Selection
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def get_launcher_for_script(script_path):
       """Automatically select appropriate launcher based on file extension."""
       
       if script_path.endswith('.bonsai'):
           from openscope_experimental_launcher.launchers import BonsaiLauncher
           return BonsaiLauncher()
       elif script_path.endswith('.py'):
           from openscope_experimental_launcher.launchers import PythonLauncher
           return PythonLauncher()
       elif script_path.endswith('.m'):
           from openscope_experimental_launcher.launchers import MATLABLauncher
           return MATLABLauncher()
       else:
           from openscope_experimental_launcher.launchers import BaseLauncher
           return BaseLauncher()
