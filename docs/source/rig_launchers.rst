Launchers
=========

The OpenScope Experimental Launcher provides a modular architecture with specialized launchers for different experimental environments. Each launcher is built on a common base and handles specific interfaces (Bonsai, MATLAB, Python) with process management and monitoring.

Overview
--------

.. list-table:: Launcher Comparison
   :header-rows: 1
   :widths: 20 25 25 30

   * - Launcher
     - Use Case
     - Interface
     - Special Features
   * - BonsaiLauncher
     - Bonsai workflows
     - Bonsai workflows (.bonsai)
     - Git management, Windows job objects
   * - MATLABLauncher
     - MATLAB scripts
     - MATLAB scripts (.m)
     - MATLAB engine, GPU support
   * - PythonLauncher
     - Python experiments
     - Python scripts (.py)
     - Environment management, package handling

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
- Cross-platform process handling

**Output:**
- Session .pkl file with experiment metadata
- Standardized logging and monitoring data

Bonsai Launcher
---------------

Specialized launcher for Bonsai visual programming workflows.

.. code-block:: python

   from openscope_experimental_launcher.launchers import BonsaiLauncher

   launcher = BonsaiLauncher()
   success = launcher.run("bonsai_parameters.json")

   if success:
       print(f"Session data: {launcher.session_pkl_path}")
       print(f"Process log: {launcher.process_log}")

**Enhanced Features:**
- Git repository management and workflow checkout
- Windows job objects for robust process control
- Bonsai-specific parameter validation
- Workflow path resolution and validation
- Real-time process monitoring

**Required Parameters:**

.. code-block:: json

   {
       "repository_url": "https://github.com/user/workflow.git",
       "script_path": "path/to/workflow.bonsai",
       "OutputFolder": "C:/experiment_data"
   }

MATLAB Launcher
---------------

Specialized launcher for MATLAB-based experiments.

.. code-block:: python

   from openscope_experimental_launcher.launchers import MATLABLauncher

   launcher = MATLABLauncher()
   success = launcher.run("matlab_parameters.json")

**Enhanced Features:**
- MATLAB engine integration
- Script path validation and execution
- GPU detection and configuration
- Environment variable management
- Cross-platform MATLAB support

**Required Parameters:**

.. code-block:: json

   {
       "script_path": "path/to/script.m",
       "OutputFolder": "C:/experiment_data"
   }

Python Launcher
---------------

Specialized launcher for Python-based experiments.

.. code-block:: python

   from openscope_experimental_launcher.launchers import PythonLauncher

   launcher = PythonLauncher()
   success = launcher.run("python_parameters.json")

**Enhanced Features:**
- Python environment management
- Package and dependency handling
- Script execution with proper isolation
- Cross-platform Python support
- Real-time output capture

**Required Parameters:**

.. code-block:: json

   {
       "script_path": "path/to/script.py",
       "OutputFolder": "C:/experiment_data"
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

Modular Architecture Benefits
-----------------------------

The new modular architecture provides several advantages:

**Separation of Concerns:**
- Launchers handle process management and monitoring
- Interfaces handle process creation
- Utilities provide shared functionality

**Flexibility:**
- Mix and match launchers with different interfaces
- Easy to add new interfaces (e.g., Julia, R)
- Stateless interfaces for better testing

**Maintainability:**
- Clear separation between launcher logic and interface logic
- Easier to extend and modify individual components
- Better code reusability

Launcher Selection Guide
------------------------

Choose the appropriate launcher based on your experiment type:

**Use BonsaiLauncher when:**
- Running Bonsai visual programming workflows
- Need Git repository management
- Working with .bonsai workflow files
- Require Windows-specific process management

**Use MATLABLauncher when:**
- Running MATLAB-based experiments
- Need MATLAB engine integration
- Working with .m script files
- Require GPU configuration

**Use PythonLauncher when:**
- Running Python-based experiments
- Need environment management
- Working with .py script files
- Require package dependency handling

**Use BaseLauncher when:**
- Creating custom implementations
- Need minimal process management
- Working with simple command-line tools
- Prototyping new launcher types

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

Advanced Usage
--------------

Script-based Execution
~~~~~~~~~~~~~~~~~~~~~~

Use the provided scripts for common scenarios:

.. code-block:: bash

   # Minimalist launcher (no Git dependencies)
   python scripts/minimalist_launcher.py parameters.json

   # Bonsai-specific launcher
   python scripts/bonsai_launcher.py parameters.json

   # Custom launcher implementation
   python scripts/custom_launcher.py parameters.json

Programmatic Usage
~~~~~~~~~~~~~~~~~~

Integrate launchers into larger systems:

.. code-block:: python

   from openscope_experimental_launcher.launchers import BonsaiLauncher

   def run_experiment_batch(parameter_files):
       """Run multiple experiments in sequence."""
       results = []
       
       for params_file in parameter_files:
           launcher = BonsaiLauncher()
           success = launcher.run(params_file)
           
           results.append({
               'params_file': params_file,
               'success': success,
               'session_uuid': launcher.session_uuid,
               'session_data': launcher.session_pkl_path
           })
       
       return results

Performance Considerations
--------------------------

**Process Management:**
- All launchers include process monitoring
- Automatic cleanup of processes and resources
- Cross-platform process handling

**Memory Usage:**
- Efficient session data serialization
- Memory monitoring during experiments
- Automatic resource cleanup

**File I/O:**
- Standardized parameter file handling
- Efficient logging and data output
- Session tracking and management
- Atomic file operations to prevent corruption

**Process Management:**
- Graceful shutdown with fallback to force termination
- Real-time stdout/stderr capture
- Robust error handling and logging

**Git Operations:**
- Efficient repository caching
- Incremental updates for existing repositories
- Parallel clone operations where possible

Troubleshooting
---------------

**Common Issues:**

1. **Launcher Import Errors**

   .. code-block:: python

      # Ensure proper package installation
      pip install -e .[dev]

2. **Missing Rig-Specific Dependencies**

   Some launchers may require additional packages:

   .. code-block:: bash

      # For SLAP2 (AIND metadata)
      pip install aind-data-schema

      # For advanced imaging analysis
      pip install numpy pandas matplotlib

3. **Parameter Validation Failures**

   Check that rig-specific parameters match expected format:

   .. code-block:: python

      # Validate parameters before running
      experiment = SLAP2Experiment()
      experiment.load_parameters("params.json")
      # Check for validation errors in logs

**Getting Help:**
- Check experiment logs for detailed error messages
- Use ``experiment.get_bonsai_errors()`` for Bonsai-specific issues
- See :doc:`troubleshooting` for comprehensive debugging guide