API Reference - Base Module
============================

The base module provides the foundational classes and utilities for all OpenScope experimental launchers.

BaseExperiment Class
--------------------

.. autoclass:: openscope_experimental_launcher.base.experiment.BaseExperiment
   :members:
   :undoc-members:
   :show-inheritance:

   The core experiment launcher class that provides Bonsai process management, parameter handling, and session tracking.

   **Key Methods:**

   .. automethod:: run
   .. automethod:: load_parameters
   .. automethod:: start_bonsai
   .. automethod:: stop
   .. automethod:: post_experiment_processing

   **Properties:**

   .. autoattribute:: session_uuid
   .. autoattribute:: mouse_id
   .. autoattribute:: user_id
   .. autoattribute:: session_output_path
   .. autoattribute:: start_time
   .. autoattribute:: stop_time

Configuration and Utilities
----------------------------

ConfigLoader
~~~~~~~~~~~~

.. autoclass:: openscope_experimental_launcher.utils.config_loader.ConfigLoader
   :members:
   :undoc-members:

   Handles loading and parsing of CamStim-style configuration files.

GitManager
~~~~~~~~~~

.. autoclass:: openscope_experimental_launcher.utils.git_manager.GitManager
   :members:
   :undoc-members:

   Manages Git repository operations including cloning, checkout, and version tracking.

ProcessMonitor
~~~~~~~~~~~~~~

.. autoclass:: openscope_experimental_launcher.utils.process_monitor.ProcessMonitor
   :members:
   :undoc-members:

   Monitors process health, memory usage, and handles cleanup operations.

Example Usage
-------------

Basic Experiment
~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.base.experiment import BaseExperiment
   import logging

   # Set up logging
   logging.basicConfig(level=logging.INFO)

   # Create experiment instance
   experiment = BaseExperiment()

   # Run with parameter file
   success = experiment.run("experiment_params.json")

   if success:
       print(f"Experiment completed successfully!")
       print(f"Session UUID: {experiment.session_uuid}")
       print(f"Output file: {experiment.session_output_path}")
       print(f"Duration: {experiment.stop_time - experiment.start_time}")
   else:
       print("Experiment failed. Check logs for details.")
       errors = experiment.get_bonsai_errors()
       print(f"Bonsai errors: {errors}")

Manual Process Control
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.base.experiment import BaseExperiment

   experiment = BaseExperiment()

   try:
       # Load parameters manually
       experiment.load_parameters("params.json")
       
       # Start Bonsai process
       experiment.start_bonsai()
       
       # Monitor progress (this blocks until completion)
       print(f"Experiment running with PID: {experiment.bonsai_process.pid}")
       
   except Exception as e:
       print(f"Error during experiment: {e}")
   finally:
       # Ensure cleanup
       experiment.stop()

Parameter Access
~~~~~~~~~~~~~~~~

.. code-block:: python

   experiment = BaseExperiment()
   experiment.load_parameters("params.json")

   # Access loaded parameters
   print(f"Mouse ID: {experiment.mouse_id}")
   print(f"User ID: {experiment.user_id}")
   print(f"Repository URL: {experiment.params['repository_url']}")
   print(f"Bonsai path: {experiment.params['bonsai_path']}")

   # Check parameter validation
   print(f"Parameter checksum: {experiment.params_checksum}")

Session Metadata
~~~~~~~~~~~~~~~~

.. code-block:: python

   experiment = BaseExperiment()
   success = experiment.run("params.json")

   if success:
       # Access session information
       session_info = {
           'uuid': experiment.session_uuid,
           'mouse_id': experiment.mouse_id,
           'user_id': experiment.user_id,
           'start_time': experiment.start_time.isoformat(),
           'end_time': experiment.stop_time.isoformat(),
           'duration_seconds': (experiment.stop_time - experiment.start_time).total_seconds(),
           'output_path': experiment.session_output_path,
           'parameter_checksum': experiment.params_checksum,
           'workflow_checksum': experiment.script_checksum
       }
       
       print(f"Session metadata: {session_info}")

Error Handling
~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.base.experiment import BaseExperiment
   import logging

   def robust_experiment_runner(params_file):
       """Run experiment with comprehensive error handling."""
       
       experiment = BaseExperiment()
       
       try:
           # Validate parameters first
           experiment.load_parameters(params_file)
           
           # Check required fields
           required_fields = ['repository_url', 'bonsai_path', 'mouse_id', 'user_id']
           missing_fields = [field for field in required_fields 
                           if not experiment.params.get(field)]
           
           if missing_fields:
               raise ValueError(f"Missing required parameters: {missing_fields}")
           
           # Run experiment
           success = experiment.run(params_file)
           
           if not success:
               # Get detailed error information
               bonsai_errors = experiment.get_bonsai_errors()
               logging.error(f"Experiment failed. Bonsai errors: {bonsai_errors}")
               
               # Check process return code
               if experiment.bonsai_process:
                   return_code = experiment.bonsai_process.returncode
                   logging.error(f"Bonsai exit code: {return_code}")
               
               return False
           
           return True
           
       except FileNotFoundError as e:
           logging.error(f"Parameter file not found: {e}")
           return False
       except ValueError as e:
           logging.error(f"Parameter validation error: {e}")
           return False
       except Exception as e:
           logging.error(f"Unexpected error: {e}")
           return False
       finally:
           # Ensure cleanup
           experiment.stop()

Constants and Enums
-------------------

Platform Information
~~~~~~~~~~~~~~~~~~~~

The base experiment automatically detects system information:

.. code-block:: python

   experiment = BaseExperiment()
   platform_info = experiment.platform_info

   # Returns dictionary with:
   # {
   #     'python': '3.11.0',
   #     'os': ('Windows', '10', '10.0.19041'),
   #     'hardware': ('Intel64 Family 6 Model 142 Stepping 10, GenuineIntel', 'AMD64'),
   #     'computer_name': 'DESKTOP-ABC123',
   #     'rig_id': 'behavior_rig_1'
   # }

Default Paths
~~~~~~~~~~~~~

.. code-block:: python

   # Default configuration locations
   DEFAULT_CONFIG_PATH = "C:/ProgramData/AIBS_MPE/camstim/config/stim.cfg"
   DEFAULT_OUTPUT_DIR = "data"
   DEFAULT_REPO_PATH = "C:/BonsaiTemp"

Windows Integration
-------------------

Process Management
~~~~~~~~~~~~~~~~~~

The base experiment uses Windows-specific APIs for robust process control:

.. code-block:: python

   # Windows job objects are automatically created
   experiment = BaseExperiment()
   
   # Check if Windows modules are available
   if experiment.hJob:
       print("Windows job object created for process management")
   else:
       print("Limited process management (Windows modules not available)")

Memory Monitoring
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Memory usage is automatically monitored during experiments
   experiment = BaseExperiment()
   experiment.run("params.json")

   # Access memory usage information
   if hasattr(experiment, '_percent_used'):
       print(f"Initial memory usage: {experiment._percent_used}%")

Extending BaseExperiment
------------------------

Creating Custom Launchers
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.base.experiment import BaseExperiment
   import logging

   class CustomExperiment(BaseExperiment):
       """Custom experiment launcher with additional features."""
       
       def __init__(self):
           super().__init__()
           self.custom_output_path = None
           logging.info("Custom experiment initialized")
       
       def load_parameters(self, param_file):
           """Override to add custom parameter validation."""
           super().load_parameters(param_file)
           
           # Add custom parameter processing
           if 'custom_setting' in self.params:
               self._validate_custom_setting(self.params['custom_setting'])
       
       def post_experiment_processing(self) -> bool:
           """Override to add custom post-processing."""
           success = super().post_experiment_processing()
           
           if success:
               # Add custom processing
               self._generate_custom_outputs()
           
           return success
       
       def _validate_custom_setting(self, setting):
           """Custom parameter validation."""
           if not isinstance(setting, str):
               raise ValueError("custom_setting must be a string")
       
       def _generate_custom_outputs(self):
           """Generate custom output files."""
           output_dir = os.path.dirname(self.session_output_path)
           self.custom_output_path = os.path.join(
               output_dir, 
               f"{os.path.basename(self.session_output_path)}_custom.json"
           )
           
           custom_data = {
               'session_uuid': self.session_uuid,
               'custom_metadata': self.params.get('custom_setting', 'default')
           }
           
           with open(self.custom_output_path, 'w') as f:
               json.dump(custom_data, f, indent=2)
           
           logging.info(f"Custom output saved: {self.custom_output_path}")

Method Reference
----------------

Core Methods
~~~~~~~~~~~~

.. py:method:: BaseExperiment.run(param_file: Optional[str] = None) -> bool

   Run the complete experiment pipeline.
   
   :param param_file: Path to JSON parameter file
   :returns: True if successful, False otherwise
   
   This method orchestrates the entire experiment execution:
   
   1. Load and validate parameters
   2. Set up Git repository
   3. Start Bonsai process
   4. Monitor execution
   5. Perform post-processing
   6. Clean up resources

.. py:method:: BaseExperiment.load_parameters(param_file: Optional[str])

   Load and validate experiment parameters.
   
   :param param_file: Path to JSON parameter file

.. py:method:: BaseExperiment.start_bonsai()

   Start the Bonsai workflow as a subprocess.
   
   Creates the Bonsai process with proper argument passing and begins monitoring.

.. py:method:: BaseExperiment.stop()

   Stop the Bonsai process gracefully.
   
   Attempts graceful termination first, then forces termination if necessary.

Utility Methods
~~~~~~~~~~~~~~~

.. py:method:: BaseExperiment.setup_output_path(output_path: Optional[str] = None) -> str

   Set up the output path for experiment data.
   
   :param output_path: Specific output path to use
   :returns: The configured output file path

.. py:method:: BaseExperiment.create_bonsai_arguments() -> List[str]

   Create command-line arguments for Bonsai.
   
   :returns: List of --property arguments for Bonsai

.. py:method:: BaseExperiment.get_bonsai_errors() -> str

   Return any errors reported by Bonsai.
   
   :returns: Concatenated error messages from stderr