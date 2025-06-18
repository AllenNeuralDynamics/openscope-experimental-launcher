Basic Usage Examples
====================

This section provides fundamental examples of using the OpenScope Experimental Launcher for common tasks.

Simple Experiment Launch
-------------------------

The most basic usage involves running a single experiment with a parameter file:

.. code-block:: python

   from openscope_experimental_launcher.base.experiment import BaseExperiment

   # Create and run basic experiment
   experiment = BaseExperiment()
   success = experiment.run("basic_params.json")   if success:
       print(f"Experiment completed successfully!")
       print(f"Output file: {experiment.session_directory}")
   else:
       print("Experiment failed - check logs for details")

**Parameter File (basic_params.json):**

.. code-block:: json   {
       "subject_id": "basic_mouse_001",
       "user_id": "researcher_name",
       "repository_url": "https://github.com/AllenNeuralDynamics/openscope-community-predictive-processing.git",
       "bonsai_path": "code/stimulus-control/src/Standard_oddball_slap2.bonsai",
       "OutputFolder": "data"
   }

Manual Parameter Loading
------------------------

For more control over the experiment process, you can load parameters manually:

.. code-block:: python

   import json
   from openscope_experimental_launcher.base.experiment import BaseExperiment

   # Load parameters manually
   with open("params.json") as f:
       params = json.load(f)   # Modify parameters programmatically
   params["subject_id"] = f"modified_{params['subject_id']}"
   params["OutputFolder"] = "custom_output"

   # Create experiment and load modified parameters
   experiment = BaseExperiment()
   experiment.params = params
   experiment.subject_id = params["subject_id"]
   experiment.user_id = params["user_id"]

   # Run with manual setup
   success = experiment.run()

Session Information Access
---------------------------

Access detailed information about completed experiments:

.. code-block:: python

   from openscope_experimental_launcher.base.experiment import BaseExperiment
   import pickle

   experiment = BaseExperiment()
   success = experiment.run("params.json")

   if success:
       # Access session metadata
       session_info = {
           'session_uuid': experiment.session_uuid,
           'subject_id': experiment.subject_id,
           'user_id': experiment.user_id,
           'start_time': experiment.start_time.isoformat(),
           'end_time': experiment.stop_time.isoformat(),
           'duration_minutes': (experiment.stop_time - experiment.start_time).total_seconds() / 60,
           'output_file': experiment.session_directory
       }

       print("Session Information:")
       for key, value in session_info.items():
           print(f"  {key}: {value}")       # Load and examine pickle output file
       pickle_file = experiment.pickle_file_path
       with open(pickle_file, 'rb') as f:
           session_data = pickle.load(f)
       
       print(f"\nOutput file contains {len(session_data)} data items")

Command Line Interface Usage
----------------------------

Using the launcher from command line:

.. code-block:: bash

   # Basic experiment
   python -m openscope_experimental_launcher.base.experiment basic_params.json

   # SLAP2 experiment
   python -m openscope_experimental_launcher.slap2.launcher slap2_params.json

Configuration File Usage
-------------------------

Using CamStim configuration files alongside parameter files:

.. code-block:: python

   from openscope_experimental_launcher.base.experiment import BaseExperiment
   from openscope_experimental_launcher.utils.config_loader import ConfigLoader

   # Load system configuration
   config_loader = ConfigLoader()
   system_config = config_loader.load("C:/ProgramData/AIBS_MPE/camstim/config/stim.cfg")

   # Use configuration values in experiment
   experiment = BaseExperiment()
   
   # Override default paths from configuration
   params = {
       "subject_id": "config_mouse_001",
       "user_id": "researcher",
       "repository_url": "https://github.com/user/repo.git",
       "bonsai_path": "workflow.bonsai",
       "OutputFolder": system_config.get('output', {}).get('base_path', 'data')
   }

   experiment.params = params
   success = experiment.run()

Error Handling Examples
-----------------------

Robust experiment execution with comprehensive error handling:

.. code-block:: python

   from openscope_experimental_launcher.base.experiment import BaseExperiment
   import logging
   import traceback

   def run_experiment_safely(param_file):
       """Run experiment with comprehensive error handling."""
       
       # Set up logging
       logging.basicConfig(
           level=logging.INFO,
           format='%(asctime)s - %(levelname)s - %(message)s',
           handlers=[
               logging.FileHandler('experiment.log'),
               logging.StreamHandler()
           ]
       )
       
       try:
           experiment = BaseExperiment()
           
           # Pre-flight checks
           logging.info("Starting pre-flight checks...")
           
           # Check parameter file exists
           if not os.path.exists(param_file):
               raise FileNotFoundError(f"Parameter file not found: {param_file}")
           
           # Load and validate parameters
           experiment.load_parameters(param_file)
           
           # Check required parameters
           required_params = ['subject_id', 'user_id', 'repository_url', 'bonsai_path']
           missing_params = [p for p in required_params if not experiment.params.get(p)]
           
           if missing_params:
               raise ValueError(f"Missing required parameters: {missing_params}")
           
           # Check disk space
           output_dir = experiment.session_directory
           if not check_disk_space(output_dir, min_gb=1.0):
               raise RuntimeError("Insufficient disk space for experiment output")
           
           logging.info("Pre-flight checks passed")
           
           # Run experiment
           logging.info("Starting experiment...")
           success = experiment.run(param_file)
           
           if success:
               logging.info(f"Experiment completed successfully")
               logging.info(f"Output directory: {experiment.session_directory}")
               logging.info(f"Duration: {experiment.stop_time - experiment.start_time}")
               return True
           else:
               logging.error("Experiment failed")
               
               # Get detailed error information
               bonsai_errors = experiment.get_bonsai_errors()
               if bonsai_errors:
                   logging.error(f"Bonsai errors: {bonsai_errors}")
               
               return False
               
       except FileNotFoundError as e:
           logging.error(f"File not found: {e}")
           return False
       except ValueError as e:
           logging.error(f"Parameter validation error: {e}")
           return False
       except RuntimeError as e:
           logging.error(f"Runtime error: {e}")
           return False
       except Exception as e:
           logging.error(f"Unexpected error: {e}")
           logging.error(f"Traceback: {traceback.format_exc()}")
           return False
       finally:
           # Cleanup if needed
           try:
               experiment.stop()
           except:
               pass

   def check_disk_space(path, min_gb):
       """Check available disk space."""
       import shutil
       
       try:
           total, used, free = shutil.disk_usage(path)
           free_gb = free / (1024**3)
           return free_gb >= min_gb
       except:
           return False

   # Usage
   if __name__ == "__main__":
       success = run_experiment_safely("params.json")
       exit(0 if success else 1)

Multiple Launcher Comparison
----------------------------

Compare output from different launchers using the same workflow:

.. code-block:: python

   from openscope_experimental_launcher.base.experiment import BaseExperiment
   from openscope_experimental_launcher.slap2.launcher import SLAP2Experiment

   def compare_launchers(param_file):
       """Compare output from different launchers."""
       
       launchers = [
           ("Base", BaseExperiment()),
           ("SLAP2", SLAP2Experiment())
       ]
       
       results = {}
       
       for name, launcher in launchers:
           print(f"\nRunning {name} launcher...")
           
           try:
               success = launcher.run(param_file)
               
               if success:
                   results[name] = {
                       'success': True,
                       'session_uuid': launcher.session_uuid,
                       'output_directory': launcher.session_directory,
                       'duration': launcher.stop_time - launcher.start_time,
                       'launcher_specific': get_launcher_specific_info(launcher)
                   }
               else:
                   results[name] = {'success': False, 'error': 'Experiment failed'}
                   
           except Exception as e:
               results[name] = {'success': False, 'error': str(e)}
       
       # Compare results
       print("\n" + "="*50)
       print("LAUNCHER COMPARISON RESULTS")
       print("="*50)
       
       for name, result in results.items():
           print(f"\n{name} Launcher:")
           if result['success']:
               print(f"  ✅ Success")
               print(f"  📁 Output: {result['output_directory']}")
               print(f"  ⏱️  Duration: {result['duration']}")
               print(f"  🆔 UUID: {result['session_uuid']}")
               
               # Show launcher-specific information
               specific_info = result['launcher_specific']
               if specific_info:
                   print(f"  📊 Specific outputs:")
                   for key, value in specific_info.items():
                       print(f"    {key}: {value}")
           else:
               print(f"  ❌ Failed: {result['error']}")
       
       return results

   def get_launcher_specific_info(launcher):
       """Get launcher-specific information."""
       info = {}
       
       # SLAP2 specific
       if hasattr(launcher, 'stimulus_table_path'):
           info['stimulus_table'] = launcher.stimulus_table_path
       if hasattr(launcher, 'session_json_path'):
           info['session_json'] = launcher.session_json_path
         return info

   # Usage
   results = compare_launchers("shared_params.json")

Working with Output Files
-------------------------

Examples of working with different output file types:

.. code-block:: python

   import pickle
   import pandas as pd
   import json
   from datetime import datetime

   def analyze_experiment_outputs(session_path, launcher_type="base"):
       """Analyze outputs from different launcher types."""
       
       base_path = session_path.replace('.pkl', '')
       
       # Always present: base pickle file
       print(f"Analyzing outputs for: {base_path}")
       
       # Load basic session data
       with open(session_path, 'rb') as f:
           session_data = pickle.load(f)
       
       print(f"Session UUID: {session_data.get('session_uuid', 'N/A')}")
       print(f"Subject ID: {session_data.get('subject_id', 'N/A')}")
       print(f"Duration: {session_data.get('duration_seconds', 'N/A')} seconds")
       
       # SLAP2 specific outputs
       stimulus_table_path = f"{base_path}_stimulus_table.csv"
       session_json_path = f"{base_path}_session.json"
       
       if os.path.exists(stimulus_table_path):
           print(f"\n📊 SLAP2 Stimulus Table Analysis:")
           stimulus_df = pd.read_csv(stimulus_table_path)
           print(f"  Total trials: {len(stimulus_df)}")
           print(f"  Trial types: {stimulus_df['stimulus_type'].value_counts().to_dict()}")
           print(f"  Duration range: {stimulus_df['duration'].min():.2f} - {stimulus_df['duration'].max():.2f}s")
       
       if os.path.exists(session_json_path):
           print(f"\n📋 SLAP2 Session Metadata:")
           with open(session_json_path) as f:
               session_json = json.load(f)
           
           print(f"  Session type: {session_json.get('session_type', 'N/A')}")
           print(f"  Experimenter: {session_json.get('experimenter_full_name', ['N/A'])[0]}")           print(f"  Start time: {session_json.get('session_start_time', 'N/A')}")
           print(f"  Rig ID: {session_json.get('rig_id', 'N/A')}")

   # Usage examples
   analyze_experiment_outputs("data/session_base.pkl", "base")
   analyze_experiment_outputs("data/session_slap2.pkl", "slap2")

Parameter File Templates
------------------------

Templates for different experiment types:

**Basic Experiment Template:**

.. code-block:: json

   {
       "subject_id": "mouse_YYYYMMDD_##",
       "user_id": "researcher_name",
       "repository_url": "https://github.com/user/bonsai-workflow-repo.git",
       "repository_commit_hash": "main",
       "bonsai_path": "path/to/workflow.bonsai",
       "output_directory": "data",
       "notes": "Basic experiment description"
   }

**Research Lab Template:**

.. code-block:: json

   {
       "subject_id": "lab_mouse_001",
       "user_id": "lab_researcher",
       "repository_url": "https://github.com/lab/experiment-workflows.git",
       "repository_commit_hash": "v1.2.0",
       "bonsai_path": "experiments/visual_stimulus/main_workflow.bonsai",
       "bonsai_exe_path": "tools/Bonsai/Bonsai.exe",
       "output_directory": "E:/ExperimentData",
       "session_type": "visual_stimulus",
       "experiment_notes": "Visual stimulus presentation with behavioral tracking",
       "lab_specific_parameter": "lab_value"
   }

**Production Environment Template:**

.. code-block:: json

   {
       "subject_id": "prod_${DATE}_${SEQUENCE}",
       "user_id": "${EXPERIMENTER}",
       "repository_url": "https://github.com/institution/production-workflows.git",
       "repository_commit_hash": "${WORKFLOW_VERSION}",
       "local_repository_path": "C:/ProductionWorkflows",
       "bonsai_path": "workflows/standard_protocol.bonsai",
       "bonsai_exe_path": "C:/Bonsai/Bonsai.exe",
       "output_directory": "D:/ProductionData/${DATE}",
       "backup_directory": "//server/backup/experiments",
       "quality_control": {
           "min_trial_count": 100,
           "max_duration_minutes": 60,
           "required_success_rate": 0.95
       }
   }