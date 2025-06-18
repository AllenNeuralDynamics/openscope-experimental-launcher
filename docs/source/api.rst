API Reference
=============

This section provides detailed API documentation for all public classes and functions in the OpenScope Experimental Launcher.

Core Classes
------------

BaseExperiment
~~~~~~~~~~~~~~

.. autoclass:: openscope_experimental_launcher.BaseExperiment
   :members:
   :undoc-members:
   :show-inheritance:

   The base experiment class that handles the core functionality of running experiments.

   **Key Methods:**

   .. automethod:: openscope_experimental_launcher.BaseExperiment.run
   .. automethod:: openscope_experimental_launcher.BaseExperiment.load_parameters
   .. automethod:: openscope_experimental_launcher.BaseExperiment.setup_repository
   .. automethod:: openscope_experimental_launcher.BaseExperiment.start_bonsai
   .. automethod:: openscope_experimental_launcher.BaseExperiment.wait_for_completion
   .. automethod:: openscope_experimental_launcher.BaseExperiment.cleanup

   **Properties:**

   .. autoproperty:: openscope_experimental_launcher.BaseExperiment.session_output_path
   .. autoproperty:: openscope_experimental_launcher.BaseExperiment.is_running
   .. autoproperty:: openscope_experimental_launcher.BaseExperiment.has_completed

Slap2Experiment
~~~~~~~~~~~~~~~

.. autoclass:: openscope_experimental_launcher.Slap2Experiment
   :members:
   :undoc-members:
   :show-inheritance:

   Specialized experiment class for SLAP2 (Simultaneous Light Activation and Photometry) experiments.

   **Additional Methods:**

   .. automethod:: openscope_experimental_launcher.Slap2Experiment.create_stimulus_table
   .. automethod:: openscope_experimental_launcher.Slap2Experiment.create_session_json
   .. automethod:: openscope_experimental_launcher.Slap2Experiment.validate_slap2_parameters

   **SLAP2-Specific Properties:**

   .. autoproperty:: openscope_experimental_launcher.Slap2Experiment.stimulus_table_path
   .. autoproperty:: openscope_experimental_launcher.Slap2Experiment.session_json_path
   .. autoproperty:: openscope_experimental_launcher.Slap2Experiment.pickle_file_path

Data Models
-----------

Session Schema
~~~~~~~~~~~~~~

The session data model follows the AIND data schema format:

.. code-block:: python

   class SessionData:
       """Session data structure based on AIND schema."""
       
       describedBy: str = "https://raw.githubusercontent.com/AllenNeuralDynamics/aind-data-schema/main/src/aind_data_schema/core/session.py"
       schema_version: str = "1.1.2"
       protocol_id: List[str] = []
       experimenter_full_name: List[str] = []
       session_start_time: str = ""
       session_end_time: str = ""
       session_type: str = ""
       iacuc_protocol: Optional[str] = None
       rig_id: str = ""
       calibrations: List = []
       maintenance: List = []
       subject_id: str = ""
       animal_weight_prior: Optional[float] = None
       animal_weight_post: Optional[float] = None
       weight_unit: str = "gram"
       anaesthesia: Optional[str] = None
       data_streams: List = []
       stimulus_epochs: List[Dict] = []
       mouse_platform_name: str = "Fixed platform"
       active_mouse_platform: bool = False
       headframe_registration: Optional[Dict] = None
       reward_delivery: Optional[Dict] = None
       reward_consumed_total: Optional[float] = None
       reward_consumed_unit: str = "milliliter"
       notes: str = ""

Stimulus Epoch Schema
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class StimulusEpoch:
       """Stimulus epoch data structure."""
       
       stimulus_start_time: str = ""
       stimulus_end_time: str = ""
       stimulus_name: str = ""
       session_number: Optional[int] = None
       software: List[Dict] = []
       script: Dict = {}
       stimulus_modalities: List[str] = []
       stimulus_parameters: Optional[Dict] = None
       stimulus_device_names: List[str] = []
       speaker_config: Optional[Dict] = None
       light_source_config: List[Dict] = []
       objects_in_arena: Optional[Dict] = None
       output_parameters: Dict = {}
       reward_consumed_during_epoch: Optional[float] = None
       reward_consumed_unit: str = "microliter"
       trials_total: Optional[int] = None
       trials_finished: Optional[int] = None
       trials_rewarded: Optional[int] = None
       notes: str = ""

Parameter Schema
~~~~~~~~~~~~~~~~

.. code-block:: python

   class ExperimentParameters:
       """Experiment parameter schema."""
       
       # Required parameters
       subject_id: str
       user_id: str
       repository_url: str
       bonsai_path: str
       
       # Optional parameters with defaults
       repository_commit_hash: str = "main"
       local_repository_path: Optional[str] = None
       bonsai_exe_path: Optional[str] = None
       bonsai_setup_script: Optional[str] = None
       output_directory: Optional[str] = None
       
       # Experiment-specific parameters
       session_type: str = "Behavior"
       rig_id: str = "default_rig"
       stimulus_name: str = "Default Stimulus"
       trials_total: Optional[int] = None
       notes: str = ""

Utility Functions
-----------------

File Management
~~~~~~~~~~~~~~~

.. autofunction:: openscope_experimental_launcher.utils.ensure_directory_exists

   Ensure a directory exists, creating it if necessary.

   :param path: Directory path to create
   :type path: str
   :returns: True if directory exists or was created successfully
   :rtype: bool

.. autofunction:: openscope_experimental_launcher.utils.generate_timestamp

   Generate a timestamp string for file naming.

   :param format: Timestamp format (default: "%y%m%d%H%M%S")
   :type format: str
   :returns: Formatted timestamp string
   :rtype: str

.. autofunction:: openscope_experimental_launcher.utils.generate_session_uuid

   Generate a unique session identifier.

   :returns: UUID string for the session
   :rtype: str

Git Operations
~~~~~~~~~~~~~~

.. autofunction:: openscope_experimental_launcher.git_utils.clone_repository

   Clone a Git repository to a local path.

   :param repo_url: URL of the repository to clone
   :type repo_url: str
   :param local_path: Local path where repository will be cloned
   :type local_path: str
   :param commit_hash: Specific commit to checkout (optional)
   :type commit_hash: str
   :returns: True if clone was successful
   :rtype: bool

.. autofunction:: openscope_experimental_launcher.git_utils.update_repository

   Update an existing local repository.

   :param local_path: Path to local repository
   :type local_path: str
   :param commit_hash: Specific commit to checkout (optional)
   :type commit_hash: str
   :returns: True if update was successful
   :rtype: bool

Process Management
~~~~~~~~~~~~~~~~~~

.. autofunction:: openscope_experimental_launcher.process_utils.start_bonsai_process

   Start a Bonsai process with specified parameters.

   :param bonsai_exe_path: Path to Bonsai executable
   :type bonsai_exe_path: str
   :param workflow_path: Path to Bonsai workflow file
   :type workflow_path: str
   :param properties: Dictionary of properties to pass to Bonsai
   :type properties: dict
   :returns: Popen process object
   :rtype: subprocess.Popen

.. autofunction:: openscope_experimental_launcher.process_utils.wait_for_process

   Wait for a process to complete with timeout.

   :param process: Process to wait for
   :type process: subprocess.Popen
   :param timeout: Timeout in seconds (optional)
   :type timeout: float
   :returns: True if process completed successfully
   :rtype: bool

Validation Functions
~~~~~~~~~~~~~~~~~~~~

.. autofunction:: openscope_experimental_launcher.validation.validate_parameters

   Validate experiment parameters.

   :param params: Parameter dictionary to validate
   :type params: dict
   :returns: Tuple of (is_valid, error_messages)
   :rtype: tuple

.. autofunction:: openscope_experimental_launcher.validation.validate_bonsai_workflow

   Validate that a Bonsai workflow file exists and is readable.

   :param workflow_path: Path to Bonsai workflow file
   :type workflow_path: str
   :returns: True if workflow is valid
   :rtype: bool

.. autofunction:: openscope_experimental_launcher.validation.validate_git_repository

   Validate that a Git repository URL is accessible.

   :param repo_url: Repository URL to validate
   :type repo_url: str
   :returns: True if repository is accessible
   :rtype: bool

Exceptions
----------

BaseExperimentError
~~~~~~~~~~~~~~~~~~~

.. autoexception:: openscope_experimental_launcher.BaseExperimentError

   Base exception class for experiment-related errors.

ParameterValidationError
~~~~~~~~~~~~~~~~~~~~~~~~

.. autoexception:: openscope_experimental_launcher.ParameterValidationError

   Raised when experiment parameters fail validation.

RepositoryError
~~~~~~~~~~~~~~~

.. autoexception:: openscope_experimental_launcher.RepositoryError

   Raised when Git repository operations fail.

BonsaiProcessError
~~~~~~~~~~~~~~~~~~

.. autoexception:: openscope_experimental_launcher.BonsaiProcessError

   Raised when Bonsai process operations fail.

Constants
---------

Default Values
~~~~~~~~~~~~~~

.. autodata:: openscope_experimental_launcher.DEFAULT_BONSAI_PATHS

   List of common Bonsai installation paths.

.. autodata:: openscope_experimental_launcher.DEFAULT_OUTPUT_DIRECTORY

   Default directory for experiment outputs.

.. autodata:: openscope_experimental_launcher.DEFAULT_TIMEOUT_SECONDS

   Default timeout for experiment completion.

File Extensions
~~~~~~~~~~~~~~~

.. autodata:: openscope_experimental_launcher.BONSAI_FILE_EXTENSION

   File extension for Bonsai workflow files.

.. autodata:: openscope_experimental_launcher.PARAMETER_FILE_EXTENSION

   File extension for parameter files.

.. autodata:: openscope_experimental_launcher.SESSION_FILE_EXTENSION

   File extension for session data files.

Example Usage Patterns
-----------------------

Basic Experiment Run
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher import BaseExperiment
   
   # Create and run experiment
   experiment = BaseExperiment()
   success = experiment.run("parameters.json")
   
   if success:
       print(f"Experiment completed successfully")
       print(f"Output saved to: {experiment.session_output_path}")
   else:
       print("Experiment failed")

Advanced Parameter Validation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher import BaseExperiment
   from openscope_experimental_launcher.validation import validate_parameters
   import json
   
   # Load and validate parameters before running
   with open("parameters.json") as f:
       params = json.load(f)
   
   is_valid, errors = validate_parameters(params)
   
   if not is_valid:
       print("Parameter validation failed:")
       for error in errors:
           print(f"  - {error}")
   else:
       experiment = BaseExperiment()
       success = experiment.run("parameters.json")

Custom Experiment Subclass
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher import BaseExperiment
   
   class CustomExperiment(BaseExperiment):
       """Custom experiment with additional functionality."""
       
       def __init__(self):
           super().__init__()
           self.custom_parameter = None
       
       def load_parameters(self, param_file):
           """Load parameters with custom validation."""
           super().load_parameters(param_file)
           
           # Add custom parameter handling
           if 'custom_parameter' in self.params:
               self.custom_parameter = self.params['custom_parameter']
               self.validate_custom_parameter()
       
       def validate_custom_parameter(self):
           """Validate custom parameter."""
           if self.custom_parameter is None:
               raise ValueError("Custom parameter is required")
       
       def create_custom_output(self):
           """Create custom output files."""
           custom_data = {
               'custom_parameter': self.custom_parameter,
               'timestamp': self.session_start_time.isoformat()
           }
           
           custom_file = self.session_output_path.replace('.json', '_custom.json')
           with open(custom_file, 'w') as f:
               json.dump(custom_data, f, indent=2)
   
   # Usage
   experiment = CustomExperiment()
   success = experiment.run("custom_parameters.json")

Asynchronous Experiment Execution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import asyncio
   from openscope_experimental_launcher import BaseExperiment
   
   async def run_experiment_async(param_file):
       """Run experiment asynchronously."""
       experiment = BaseExperiment()
       
       # Run in executor to avoid blocking
       loop = asyncio.get_event_loop()
       success = await loop.run_in_executor(
           None, experiment.run, param_file
       )
       
       return success, experiment
   
   async def run_multiple_experiments(param_files):
       """Run multiple experiments concurrently."""
       tasks = [run_experiment_async(pf) for pf in param_files]
       results = await asyncio.gather(*tasks)
       
       for i, (success, experiment) in enumerate(results):
           param_file = param_files[i]
           if success:
               print(f"✅ {param_file}: {experiment.session_output_path}")
           else:
               print(f"❌ {param_file}: Failed")
   
   # Usage
   param_files = ["exp1.json", "exp2.json", "exp3.json"]
   asyncio.run(run_multiple_experiments(param_files))

Error Handling and Logging
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import logging
   from openscope_experimental_launcher import BaseExperiment
   from openscope_experimental_launcher.exceptions import (
       ParameterValidationError,
       RepositoryError,
       BonsaiProcessError
   )
   
   # Set up logging
   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)
   
   def run_experiment_with_error_handling(param_file):
       """Run experiment with comprehensive error handling."""
       
       try:
           experiment = BaseExperiment()
           success = experiment.run(param_file)
           
           if success:
               logger.info(f"Experiment completed: {experiment.session_output_path}")
               return True
           else:
               logger.error("Experiment failed for unknown reasons")
               return False
               
       except ParameterValidationError as e:
           logger.error(f"Parameter validation failed: {e}")
           return False
           
       except RepositoryError as e:
           logger.error(f"Repository operation failed: {e}")
           return False
           
       except BonsaiProcessError as e:
           logger.error(f"Bonsai process failed: {e}")
           return False
           
       except Exception as e:
           logger.exception(f"Unexpected error: {e}")
           return False
   
   # Usage
   success = run_experiment_with_error_handling("parameters.json")