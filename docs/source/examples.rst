Examples
========

This section provides practical examples of using the OpenScope Experimental Launcher in various scenarios.

.. toctree::
   :maxdepth: 2

   examples/basic_usage
   examples/slap2_workflows
   examples/mindscope_integration
   examples/custom_launchers
   examples/batch_processing
   examples/error_handling

Working Examples
================

This section provides complete, working examples of using the OpenScope Experimental Launcher for different experimental scenarios.

Basic Experiment Example
-------------------------

Complete Basic Workflow
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python
   :caption: basic_experiment_example.py

   """
   Complete example of running a basic OpenScope experiment.
   """
   
   import logging
   import json
   from pathlib import Path
   from openscope_experimental_launcher.base.experiment import BaseExperiment

   # Set up logging
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(levelname)s - %(message)s'
   )

   def create_basic_parameters():
       """Create a basic parameter file for testing."""
       params = {
           "mouse_id": "example_mouse_001",
           "user_id": "researcher_jane",
           "repository_url": "https://github.com/AllenNeuralDynamics/openscope-community-predictive-processing.git",
           "repository_commit_hash": "main",
           "local_repository_path": "C:/BonsaiExperiments/BasicExample",
           "bonsai_path": "code/stimulus-control/src/Standard_oddball_slap2.bonsai",
           "bonsai_exe_path": "code/stimulus-control/bonsai/Bonsai.exe",
           "output_directory": "C:/ExperimentData/BasicExample",
           "session_type": "basic_experiment"
       }
       
       # Save parameter file
       param_file = "basic_experiment_params.json"
       with open(param_file, 'w') as f:
           json.dump(params, f, indent=2)
       
       return param_file

   def run_basic_experiment():
       """Run a complete basic experiment with error handling."""
       
       try:
           # Create parameter file
           param_file = create_basic_parameters()
           print(f"Created parameter file: {param_file}")
           
           # Create experiment instance
           experiment = BaseExperiment()
           
           # Run the experiment
           print("Starting experiment...")
           success = experiment.run(param_file)
           
           if success:
               print("✅ Experiment completed successfully!")
               print(f"Session UUID: {experiment.session_uuid}")
               print(f"Output file: {experiment.session_output_path}")
               print(f"Duration: {experiment.stop_time - experiment.start_time}")
               
               # Show session metadata
               print("\nSession Metadata:")
               print(f"  Mouse ID: {experiment.mouse_id}")
               print(f"  User ID: {experiment.user_id}")
               print(f"  Parameter checksum: {experiment.params_checksum}")
               print(f"  Workflow checksum: {experiment.script_checksum}")
               
           else:
               print("❌ Experiment failed!")
               errors = experiment.get_bonsai_errors()
               if errors:
                   print(f"Bonsai errors: {errors}")
           
           return success
           
       except Exception as e:
           print(f"❌ Error running experiment: {e}")
           return False
       
       finally:
           # Cleanup
           if 'experiment' in locals():
               experiment.stop()

   if __name__ == "__main__":
       success = run_basic_experiment()
       exit(0 if success else 1)

SLAP2 Imaging Example
---------------------

Complete SLAP2 Workflow
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python
   :caption: slap2_experiment_example.py

   """
   Complete example of running a SLAP2 imaging experiment with full metadata generation.
   """
   
   import logging
   import json
   import pandas as pd
   from openscope_experimental_launcher.slap2.launcher import SLAP2Experiment

   # Configure logging
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )

   def create_slap2_parameters():
       """Create comprehensive SLAP2 parameter file."""
       params = {
           "mouse_id": "slap2_mouse_20250613_001",
           "user_id": "imaging_researcher",
           "repository_url": "https://github.com/AllenNeuralDynamics/openscope-community-predictive-processing.git",
           "repository_commit_hash": "v1.2.0",
           "local_repository_path": "C:/BonsaiExperiments/SLAP2",
           "bonsai_path": "code/stimulus-control/src/Standard_oddball_slap2.bonsai",
           "bonsai_exe_path": "code/stimulus-control/bonsai/Bonsai.exe",
           "output_directory": "C:/ExperimentData/SLAP2",
           
           # SLAP2-specific parameters
           "session_type": "SLAP2",
           "rig_id": "slap2_rig_behavior_room_2",
           "experimenter_name": "Dr. Jane Smith",
           "laser_power": 12.5,
           "laser_wavelength": 920,
           "num_trials": 500,
           
           # Field of view configuration
           "slap_fovs": [
               {
                   "index": 0,
                   "imaging_depth": 200,
                   "targeted_structure": "Primary Visual Cortex",
                   "fov_coordinate_ml": 3.0,
                   "fov_coordinate_ap": -3.2,
                   "fov_reference": "Bregma",
                   "fov_width": 512,
                   "fov_height": 512,
                   "magnification": "40x",
                   "frame_rate": 30.0,
                   "session_type": "Parent"
               },
               {
                   "index": 1,
                   "imaging_depth": 350,
                   "targeted_structure": "Layer 5 Visual Cortex",
                   "fov_coordinate_ml": 3.0,
                   "fov_coordinate_ap": -3.2,
                   "fov_reference": "Bregma",
                   "fov_width": 256,
                   "fov_height": 256,
                   "magnification": "60x",
                   "frame_rate": 15.0,
                   "session_type": "Child"
               }
           ],
           
           # Bonsai workflow parameters
           "bonsai_parameters": {
               "TrialDuration": 8.0,
               "BaselineTime": 1.0,
               "StimulusTime": 2.0,
               "InterTrialInterval": 3.0
           }
       }
       
       param_file = "slap2_experiment_params.json"
       with open(param_file, 'w') as f:
           json.dump(params, f, indent=2)
       
       return param_file

   def analyze_slap2_outputs(experiment):
       """Analyze SLAP2 experiment outputs."""
       
       print("\n=== SLAP2 Output Analysis ===")
       
       # Analyze stimulus table
       if experiment.stimulus_table_path and Path(experiment.stimulus_table_path).exists():
           df = pd.read_csv(experiment.stimulus_table_path)
           print(f"📊 Stimulus Table Analysis:")
           print(f"  Total trials: {len(df)}")
           print(f"  Columns: {list(df.columns)}")
           print(f"  Duration: {df['stop_time'].max():.1f} seconds")
           
           if 'stimulus_type' in df.columns:
               stimulus_counts = df['stimulus_type'].value_counts()
               print(f"  Stimulus types: {dict(stimulus_counts)}")
       
       # Analyze session metadata
       if experiment.session_json_path and Path(experiment.session_json_path).exists():
           with open(experiment.session_json_path) as f:
               session_data = json.load(f)
           
           print(f"📝 Session Metadata:")
           print(f"  Session type: {session_data.get('session_type')}")
           print(f"  Start time: {session_data.get('session_start_time')}")
           print(f"  End time: {session_data.get('session_end_time')}")
           print(f"  Experimenter: {session_data.get('experimenter_full_name')}")
           
           if 'stimulus_epochs' in session_data:
               print(f"  Stimulus epochs: {len(session_data['stimulus_epochs'])}")

   def run_slap2_experiment():
       """Run complete SLAP2 experiment with analysis."""
       
       try:
           # Create parameters
           param_file = create_slap2_parameters()
           print(f"Created SLAP2 parameter file: {param_file}")
           
           # Create SLAP2 experiment
           experiment = SLAP2Experiment()
           
           # Run experiment
           print("🚀 Starting SLAP2 experiment...")
           success = experiment.run(param_file)
           
           if success:
               print("✅ SLAP2 experiment completed successfully!")
               
               # Show output files
               print(f"\n📁 Output Files:")
               print(f"  Session data: {experiment.session_output_path}")
               print(f"  Stimulus table: {experiment.stimulus_table_path}")
               print(f"  Session metadata: {experiment.session_json_path}")
               
               # Analyze outputs
               analyze_slap2_outputs(experiment)
               
           else:
               print("❌ SLAP2 experiment failed!")
               errors = experiment.get_bonsai_errors()
               if errors:
                   print(f"Bonsai errors: {errors}")
           
           return success
           
       except Exception as e:
           print(f"❌ Error running SLAP2 experiment: {e}")
           import traceback
           traceback.print_exc()
           return False
       
       finally:
           if 'experiment' in locals():
               experiment.stop()

   if __name__ == "__main__":
       success = run_slap2_experiment()
       exit(0 if success else 1)

Multi-Rig Compatibility Example
-------------------------------

Cross-Platform Testing
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python
   :caption: multi_rig_compatibility_example.py

   """
   Example demonstrating cross-rig compatibility by running the same workflow
   on different launcher types.
   """
   
   import logging
   import json
   from pathlib import Path
   from openscope_experimental_launcher.base.experiment import BaseExperiment
   from openscope_experimental_launcher.slap2.launcher import SLAP2Experiment
   from openscope_experimental_launcher.mindscope import (
       ClusterExperiment, MesoscopeExperiment, NeuropixelExperiment
   )

   logging.basicConfig(level=logging.INFO)

   def create_universal_parameters():
       """Create parameters that work across all launcher types."""
       params = {
           "mouse_id": "multi_rig_mouse_001",
           "user_id": "cross_platform_researcher",
           "repository_url": "https://github.com/AllenNeuralDynamics/openscope-community-predictive-processing.git",
           "bonsai_path": "code/stimulus-control/src/Standard_oddball_slap2.bonsai",
           "output_directory": "C:/MultiRigTest",
           "session_type": "compatibility_test",
           "num_trials": 50  # Shorter for testing
       }
       
       param_file = "universal_params.json"
       with open(param_file, 'w') as f:
           json.dump(params, f, indent=2)
       
       return param_file

   def test_launcher(launcher_class, launcher_name, param_file):
       """Test a specific launcher with error handling."""
       
       print(f"\n🧪 Testing {launcher_name}...")
       
       try:
           experiment = launcher_class()
           success = experiment.run(param_file)
           
           result = {
               'launcher': launcher_name,
               'success': success,
               'session_uuid': experiment.session_uuid if success else None,
               'output_path': experiment.session_output_path if success else None,
               'duration': None
           }
           
           if success:
               duration = experiment.stop_time - experiment.start_time
               result['duration'] = duration.total_seconds()
               print(f"  ✅ {launcher_name} completed in {duration.total_seconds():.1f}s")
               
               # Add launcher-specific info
               if hasattr(experiment, 'stimulus_table_path'):
                   result['stimulus_table'] = experiment.stimulus_table_path
               if hasattr(experiment, 'session_json_path'):
                   result['session_json'] = experiment.session_json_path
               if hasattr(experiment, 'pickle_file_path'):
                   result['pickle_metadata'] = experiment.pickle_file_path
                   result['pickle_summary'] = experiment.get_pickle_data_summary()
           else:
               print(f"  ❌ {launcher_name} failed")
               errors = experiment.get_bonsai_errors()
               result['errors'] = errors
           
           return result
           
       except Exception as e:
           print(f"  💥 {launcher_name} crashed: {e}")
           return {
               'launcher': launcher_name,
               'success': False,
               'error': str(e)
           }

   def run_compatibility_test():
       """Run compatibility test across all launcher types."""
       
       print("🔄 Multi-Rig Compatibility Test")
       print("=" * 50)
       
       # Create universal parameter file
       param_file = create_universal_parameters()
       print(f"Created universal parameter file: {param_file}")
       
       # Define launchers to test
       launchers = [
           (BaseExperiment, "BaseExperiment"),
           (SLAP2Experiment, "SLAP2Experiment"),
           (ClusterExperiment, "ClusterExperiment"),
           (MesoscopeExperiment, "MesoscopeExperiment"),
           (NeuropixelExperiment, "NeuropixelExperiment")
       ]
       
       results = []
       
       # Test each launcher
       for launcher_class, launcher_name in launchers:
           result = test_launcher(launcher_class, launcher_name, param_file)
           results.append(result)
       
       # Summary report
       print(f"\n📊 Compatibility Test Results")
       print("=" * 50)
       
       successful_launchers = [r for r in results if r['success']]
       failed_launchers = [r for r in results if not r['success']]
       
       print(f"✅ Successful: {len(successful_launchers)}/{len(results)}")
       print(f"❌ Failed: {len(failed_launchers)}/{len(results)}")
       
       if successful_launchers:
           print(f"\n🎉 Working Launchers:")
           for result in successful_launchers:
               duration = result.get('duration', 0)
               print(f"  • {result['launcher']}: {duration:.1f}s")
       
       if failed_launchers:
           print(f"\n⚠️  Failed Launchers:")
           for result in failed_launchers:
               launcher = result['launcher']
               error = result.get('error', 'Unknown error')
               print(f"  • {launcher}: {error}")
       
       # Detailed output comparison
       print(f"\n📁 Output File Comparison:")
       for result in successful_launchers:
           launcher = result['launcher']
           print(f"\n  {launcher}:")
           if 'output_path' in result:
               print(f"    Session file: {Path(result['output_path']).name}")
           if 'stimulus_table' in result:
               print(f"    Stimulus table: {Path(result['stimulus_table']).name}")
           if 'session_json' in result:
               print(f"    Session JSON: {Path(result['session_json']).name}")
           if 'pickle_metadata' in result:
               summary = result.get('pickle_summary', {})
               rig_type = summary.get('rig_type', 'unknown')
               print(f"    Pickle metadata: {Path(result['pickle_metadata']).name} ({rig_type})")
       
       return len(successful_launchers) == len(results)

   if __name__ == "__main__":
       all_passed = run_compatibility_test()
       print(f"\n{'🎉 All tests passed!' if all_passed else '⚠️  Some tests failed.'}")
       exit(0 if all_passed else 1)

Batch Processing Example
------------------------

Automated Batch Experiments
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python
   :caption: batch_processing_example.py

   """
   Example of running multiple experiments in batch mode with different configurations.
   """
   
   import logging
   import json
   import time
   from datetime import datetime
   from pathlib import Path
   from openscope_experimental_launcher.slap2.launcher import SLAP2Experiment

   logging.basicConfig(level=logging.INFO)

   def create_batch_parameters():
       """Create multiple parameter files for batch processing."""
       
       base_params = {
           "user_id": "batch_researcher", 
           "repository_url": "https://github.com/AllenNeuralDynamics/openscope-community-predictive-processing.git",
           "bonsai_path": "code/stimulus-control/src/Standard_oddball_slap2.bonsai",
           "output_directory": "C:/BatchExperiments",
           "session_type": "SLAP2",
           "laser_wavelength": 920,
           "num_trials": 100
       }
       
       # Different experimental conditions
       conditions = [
           {
               "condition_name": "low_power",
               "mouse_id": "batch_mouse_001_low",
               "laser_power": 8.0,
               "experimenter_name": "Researcher A"
           },
           {
               "condition_name": "medium_power", 
               "mouse_id": "batch_mouse_002_med",
               "laser_power": 12.5,
               "experimenter_name": "Researcher B"
           },
           {
               "condition_name": "high_power",
               "mouse_id": "batch_mouse_003_high", 
               "laser_power": 18.0,
               "experimenter_name": "Researcher C"
           }
       ]
       
       param_files = []
       
       for condition in conditions:
           # Merge base parameters with condition-specific ones
           params = {**base_params, **condition}
           
           # Create FOV configuration
           params["slap_fovs"] = [
               {
                   "index": 0,
                   "imaging_depth": 200,
                   "targeted_structure": "V1",
                   "fov_coordinate_ml": 2.5,
                   "fov_coordinate_ap": -2.0,
                   "fov_reference": "Bregma",
                   "fov_width": 512,
                   "fov_height": 512,
                   "magnification": "40x",
                   "frame_rate": 30.0,
                   "session_type": "Parent"
               }
           ]
           
           # Save parameter file
           param_file = f"batch_params_{condition['condition_name']}.json"
           with open(param_file, 'w') as f:
               json.dump(params, f, indent=2)
           
           param_files.append({
               'file': param_file,
               'condition': condition['condition_name'],
               'mouse_id': condition['mouse_id']
           })
       
       return param_files

   def run_batch_experiment(param_info):
       """Run a single experiment in the batch."""
       
       param_file = param_info['file']
       condition = param_info['condition']
       
       print(f"\n🚀 Starting batch experiment: {condition}")
       print(f"   Parameter file: {param_file}")
       
       start_time = time.time()
       
       try:
           experiment = SLAP2Experiment()
           success = experiment.run(param_file)
           
           duration = time.time() - start_time
           
           result = {
               'condition': condition,
               'param_file': param_file,
               'success': success,
               'duration_seconds': duration,
               'start_time': datetime.now().isoformat(),
           }
           
           if success:
               result.update({
                   'session_uuid': experiment.session_uuid,
                   'mouse_id': experiment.mouse_id,
                   'output_path': experiment.session_output_path,
                   'stimulus_table': experiment.stimulus_table_path,
                   'session_json': experiment.session_json_path
               })
               
               print(f"   ✅ Completed in {duration:.1f}s")
               print(f"   Session UUID: {experiment.session_uuid}")
           else:
               errors = experiment.get_bonsai_errors()
               result['errors'] = errors
               print(f"   ❌ Failed after {duration:.1f}s")
               if errors:
                   print(f"   Errors: {errors}")
           
           return result
           
       except Exception as e:
           duration = time.time() - start_time
           print(f"   💥 Crashed after {duration:.1f}s: {e}")
           return {
               'condition': condition,
               'param_file': param_file,
               'success': False,
               'duration_seconds': duration,
               'error': str(e)
           }

   def run_batch_processing():
       """Run complete batch processing workflow."""
       
       print("🔄 SLAP2 Batch Processing")
       print("=" * 50)
       
       # Create parameter files
       param_files = create_batch_parameters()
       print(f"Created {len(param_files)} parameter files for batch processing")
       
       # Run experiments
       results = []
       total_start_time = time.time()
       
       for i, param_info in enumerate(param_files, 1):
           print(f"\n[{i}/{len(param_files)}] Processing condition: {param_info['condition']}")
           result = run_batch_experiment(param_info)
           results.append(result)
       
       total_duration = time.time() - total_start_time
       
       # Generate batch report
       print(f"\n📊 Batch Processing Report")
       print("=" * 50)
       
       successful = [r for r in results if r['success']]
       failed = [r for r in results if not r['success']]
       
       print(f"Total experiments: {len(results)}")
       print(f"Successful: {len(successful)}")
       print(f"Failed: {len(failed)}")
       print(f"Total duration: {total_duration:.1f}s")
       print(f"Average per experiment: {total_duration/len(results):.1f}s")
       
       if successful:
           print(f"\n✅ Successful Experiments:")
           for result in successful:
               condition = result['condition']
               duration = result['duration_seconds']
               mouse_id = result.get('mouse_id', 'unknown')
               print(f"  • {condition} ({mouse_id}): {duration:.1f}s")
       
       if failed:
           print(f"\n❌ Failed Experiments:")
           for result in failed:
               condition = result['condition']
               error = result.get('error', result.get('errors', 'Unknown error'))
               print(f"  • {condition}: {error}")
       
       # Save batch results
       batch_report = {
           'batch_start_time': datetime.now().isoformat(),
           'total_experiments': len(results),
           'successful_count': len(successful),
           'failed_count': len(failed),
           'total_duration_seconds': total_duration,
           'results': results
       }
       
       report_file = f"batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
       with open(report_file, 'w') as f:
           json.dump(batch_report, f, indent=2)
       
       print(f"\n📄 Batch report saved: {report_file}")
       
       return len(failed) == 0

   if __name__ == "__main__":
       all_successful = run_batch_processing()
       exit(0 if all_successful else 1)

Error Handling and Recovery Example
-----------------------------------

Robust Experiment Runner
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python
   :caption: robust_experiment_example.py

   """
   Example demonstrating robust error handling and recovery strategies.
   """
   
   import logging
   import json
   import time
   import shutil
   from pathlib import Path
   from openscope_experimental_launcher.base.experiment import BaseExperiment

   # Configure detailed logging
   logging.basicConfig(
       level=logging.DEBUG,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
       handlers=[
           logging.FileHandler('experiment_debug.log'),
           logging.StreamHandler()
       ]
   )

   class RobustExperimentRunner:
       """Robust experiment runner with error handling and recovery."""
       
       def __init__(self, max_retries=3, backup_enabled=True):
           self.max_retries = max_retries
           self.backup_enabled = backup_enabled
           self.logger = logging.getLogger(__name__)
       
       def validate_environment(self):
           """Validate experimental environment before running."""
           
           self.logger.info("Validating experimental environment...")
           
           # Check disk space
           output_dir = Path("C:/ExperimentData")
           if output_dir.exists():
               free_space = shutil.disk_usage(output_dir).free
               free_space_gb = free_space / (1024**3)
               
               if free_space_gb < 1.0:  # Less than 1GB free
                   raise RuntimeError(f"Insufficient disk space: {free_space_gb:.1f}GB free")
               
               self.logger.info(f"Disk space OK: {free_space_gb:.1f}GB free")
           
           # Check critical paths exist
           critical_paths = ["C:/Windows/System32"]  # Example
           for path in critical_paths:
               if not Path(path).exists():
                   raise RuntimeError(f"Critical path missing: {path}")
           
           self.logger.info("Environment validation passed")
       
       def create_backup(self, param_file):
           """Create backup of parameter file."""
           
           if not self.backup_enabled:
               return None
           
           backup_file = f"{param_file}.backup"
           shutil.copy2(param_file, backup_file)
           self.logger.info(f"Created parameter backup: {backup_file}")
           return backup_file
       
       def run_with_retry(self, param_file):
           """Run experiment with retry logic."""
           
           for attempt in range(1, self.max_retries + 1):
               self.logger.info(f"Experiment attempt {attempt}/{self.max_retries}")
               
               try:
                   # Validate environment
                   self.validate_environment()
                   
                   # Create backup
                   backup_file = self.create_backup(param_file)
                   
                   # Run experiment
                   experiment = BaseExperiment()
                   success = experiment.run(param_file)
                   
                   if success:
                       self.logger.info(f"Experiment succeeded on attempt {attempt}")
                       return True, experiment, None
                   else:
                       # Get error details
                       errors = experiment.get_bonsai_errors()
                       self.logger.warning(f"Experiment failed on attempt {attempt}: {errors}")
                       
                       if attempt < self.max_retries:
                           # Wait before retry
                           wait_time = attempt * 5  # Exponential backoff
                           self.logger.info(f"Waiting {wait_time}s before retry...")
                           time.sleep(wait_time)
                       else:
                           return False, experiment, errors
               
               except Exception as e:
                   self.logger.error(f"Experiment crashed on attempt {attempt}: {e}")
                   
                   if attempt < self.max_retries:
                       wait_time = attempt * 10
                       self.logger.info(f"Waiting {wait_time}s before retry...")
                       time.sleep(wait_time)
                   else:
                       return False, None, str(e)
           
           return False, None, "Max retries exceeded"
       
       def run_robust_experiment(self, param_file):
           """Run experiment with full error handling and recovery."""
           
           self.logger.info("Starting robust experiment runner")
           
           try:
               # Run with retry
               success, experiment, error = self.run_with_retry(param_file)
               
               if success:
                   self.logger.info("✅ Experiment completed successfully")
                   
                   # Generate success report
                   report = {
                       'status': 'success',
                       'session_uuid': experiment.session_uuid,
                       'output_path': experiment.session_output_path,
                       'duration_seconds': (experiment.stop_time - experiment.start_time).total_seconds(),
                       'parameter_checksum': experiment.params_checksum
                   }
                   
                   return report
               
               else:
                   self.logger.error("❌ Experiment failed after all retries")
                   
                   # Generate failure report
                   report = {
                       'status': 'failed',
                       'error': error,
                       'max_retries_reached': True
                   }
                   
                   # Attempt data recovery if experiment partially ran
                   if experiment:
                       self.logger.info("Attempting partial data recovery...")
                       partial_data = self.recover_partial_data(experiment)
                       if partial_data:
                           report['partial_data'] = partial_data
                   
                   return report
           
           except Exception as e:
               self.logger.critical(f"💥 Critical error in robust runner: {e}")
               return {
                   'status': 'critical_error',
                   'error': str(e)
               }
       
       def recover_partial_data(self, experiment):
           """Attempt to recover partial data from failed experiment."""
           
           partial_data = {}
           
           try:
               if hasattr(experiment, 'session_uuid') and experiment.session_uuid:
                   partial_data['session_uuid'] = experiment.session_uuid
               
               if hasattr(experiment, 'start_time') and experiment.start_time:
                   partial_data['start_time'] = experiment.start_time.isoformat()
               
               # Check for any output files that were created
               if hasattr(experiment, 'session_output_path'):
                   output_path = Path(experiment.session_output_path)
                   if output_path.exists():
                       partial_data['partial_output_file'] = str(output_path)
                       partial_data['output_file_size'] = output_path.stat().st_size
               
               self.logger.info(f"Recovered partial data: {partial_data}")
               
           except Exception as e:
               self.logger.warning(f"Data recovery failed: {e}")
           
           return partial_data

   def create_test_parameters():
       """Create test parameters for robust runner demonstration."""
       params = {
           "mouse_id": "robust_test_mouse",
           "user_id": "robust_researcher",
           "repository_url": "https://github.com/AllenNeuralDynamics/openscope-community-predictive-processing.git",
           "bonsai_path": "code/stimulus-control/src/Standard_oddball_slap2.bonsai",
           "output_directory": "C:/RobustExperiments",
           "num_trials": 10  # Small for testing
       }
       
       param_file = "robust_test_params.json"
       with open(param_file, 'w') as f:
           json.dump(params, f, indent=2)
       
       return param_file

   def main():
       """Main function demonstrating robust experiment runner."""
       
       print("🛡️  Robust Experiment Runner Demo")
       print("=" * 50)
       
       # Create parameter file
       param_file = create_test_parameters()
       print(f"Created test parameter file: {param_file}")
       
       # Create robust runner
       runner = RobustExperimentRunner(max_retries=3, backup_enabled=True)
       
       # Run experiment
       result = runner.run_robust_experiment(param_file)
       
       # Display results
       print(f"\n📊 Experiment Result:")
       print(f"Status: {result['status']}")
       
       if result['status'] == 'success':
           print(f"✅ Success!")
           print(f"  Session UUID: {result['session_uuid']}")
           print(f"  Duration: {result['duration_seconds']:.1f}s")
           print(f"  Output: {result['output_path']}")
       
       elif result['status'] == 'failed':
           print(f"❌ Failed: {result['error']}")
           if 'partial_data' in result:
               print(f"  Partial data recovered: {result['partial_data']}")
       
       else:
           print(f"💥 Critical error: {result['error']}")
       
       return result['status'] == 'success'

   if __name__ == "__main__":
       success = main()
       exit(0 if success else 1)