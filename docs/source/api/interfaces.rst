API Reference - Interfaces Module
===================================

The interfaces module provides stateless interface classes for creating processes for different execution environments.

Interface Classes
-----------------

Bonsai Interface
~~~~~~~~~~~~~~~~

.. autoclass:: openscope_experimental_launcher.interfaces.bonsai_interface.BonsaiInterface
   :members:
   :undoc-members:

   Stateless interface for creating Bonsai workflow processes.

   **Key Methods:**

   .. automethod:: create_process
   .. automethod:: validate_workflow_path

MATLAB Interface
~~~~~~~~~~~~~~~~

.. autoclass:: openscope_experimental_launcher.interfaces.matlab_interface.MATLABInterface
   :members:
   :undoc-members:

   Stateless interface for creating MATLAB script processes.

   **Key Methods:**

   .. automethod:: create_process
   .. automethod:: validate_script_path

Python Interface
~~~~~~~~~~~~~~~~

.. autoclass:: openscope_experimental_launcher.interfaces.python_interface.PythonInterface
   :members:
   :undoc-members:

   Stateless interface for creating Python script processes.

   **Key Methods:**

   .. automethod:: create_process
   .. automethod:: validate_script_path

Interface Usage
---------------

Direct Interface Usage
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.interfaces import BonsaiInterface

   # Create a Bonsai process directly
   process = BonsaiInterface.create_process(
       bonsai_path="workflow.bonsai",
       parameters={"NumTrials": 100}
   )

   # Monitor the process
   process.wait()

Custom Launcher with Interface
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.launchers import BaseLauncher
   from openscope_experimental_launcher.interfaces import PythonInterface

   class CustomPythonLauncher(BaseLauncher):
       """Custom launcher using Python interface."""
       
       def _create_process(self, script_path, parameters):
           return PythonInterface.create_process(script_path, parameters)

Interface Testing
~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.interfaces import MATLABInterface

   # Test if MATLAB is available
   try:
       test_process = MATLABInterface.create_process(
           "test_script.m", 
           {"test_param": "value"}
       )
       print("MATLAB interface is working")
       test_process.terminate()
   except Exception as e:
       print(f"MATLAB interface error: {e}")

Design Principles
-----------------

**Stateless Design:**
All interface classes are stateless - they don't maintain any instance state between method calls. This makes them:

- Thread-safe for concurrent usage
- Easy to test and mock
- Suitable for functional programming patterns
- Cacheable and reusable

**Single Responsibility:**
Each interface handles only process creation for its specific environment:

- BonsaiInterface: Creates Bonsai workflow processes
- MATLABInterface: Creates MATLAB script processes  
- PythonInterface: Creates Python script processes

**Consistent API:**
All interfaces provide the same method signature:

.. code-block:: python

   @staticmethod
   def create_process(script_path: str, parameters: dict) -> subprocess.Popen:
       """Create a process for the given script with parameters."""
       pass
