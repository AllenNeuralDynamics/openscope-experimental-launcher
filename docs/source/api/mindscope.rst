API Reference - Mindscope Module
================================

The Mindscope module provides specialized launchers for different Mindscope rig configurations, each generating rig-specific metadata.

Overview
--------

The Mindscope module includes three specialized experiment launchers:

- **ClusterExperiment**: For cluster computing resources
- **MesoscopeExperiment**: For mesoscope (large field-of-view) imaging
- **NeuropixelExperiment**: For electrophysiology with Neuropixels probes

All Mindscope launchers extend the base functionality with rig-specific post-processing and metadata generation.

ClusterExperiment Class
-----------------------

.. autoclass:: openscope_experimental_launcher.mindscope.cluster.ClusterExperiment
   :members:
   :undoc-members:
   :show-inheritance:

   Specialized launcher for experiments run on cluster computing resources.

   **Features:**
   - Cluster resource monitoring
   - Distributed computing metadata
   - Job queue integration tracking
   - Compute node information logging

MesoscopeExperiment Class
-------------------------

.. autoclass:: openscope_experimental_launcher.mindscope.mesoscope.MesoscopeExperiment
   :members:
   :undoc-members:
   :show-inheritance:

   Specialized launcher for mesoscope (large field-of-view) imaging experiments.

   **Features:**
   - Imaging plane configuration tracking
   - Zoom level and magnification metadata
   - Frame rate and timing validation
   - Multi-plane acquisition monitoring

NeuropixelExperiment Class
--------------------------

.. autoclass:: openscope_experimental_launcher.mindscope.neuropixel.NeuropixelExperiment
   :members:
   :undoc-members:
   :show-inheritance:

   Specialized launcher for electrophysiology experiments using Neuropixels probes.

   **Features:**
   - Multi-probe configuration tracking
   - Channel mapping and validation
   - Sampling rate monitoring
   - Data rate estimation
   - LFP and spike detection parameters

Example Usage
-------------

Cluster Experiment
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.mindscope import ClusterExperiment

   # Create cluster experiment
   experiment = ClusterExperiment()
   success = experiment.run("cluster_params.json")

   if success:
       print(f"Cluster experiment completed!")
       print(f"Pickle metadata: {experiment.pickle_file_path}")
       
       # Get cluster-specific summary
       summary = experiment.get_pickle_data_summary()
       print(f"Rig type: {summary['rig_type']}")
       print(f"Duration: {summary['duration_seconds']} seconds")

Mesoscope Experiment
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.mindscope import MesoscopeExperiment

   # Create mesoscope experiment
   experiment = MesoscopeExperiment()
   success = experiment.run("mesoscope_params.json")

   if success:
       # Access mesoscope-specific metadata
       summary = experiment.get_pickle_data_summary()
       print(f"Imaging planes: {summary['num_imaging_planes']}")
       print(f"Frame rate: {summary['frame_rate_hz']} Hz")
       print(f"Zoom level: {summary['zoom_level']}")

Neuropixel Experiment
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.mindscope import NeuropixelExperiment

   # Create neuropixel experiment
   experiment = NeuropixelExperiment()
   success = experiment.run("neuropixel_params.json")

   if success:
       # Access electrophysiology metadata
       summary = experiment.get_pickle_data_summary()
       print(f"Number of probes: {summary['num_probes']}")
       print(f"Recording channels: {summary['num_recording_channels']}")
       print(f"Sampling rate: {summary['sampling_rate_hz']} Hz")
       print(f"Data rate: {summary['estimated_data_rate_mbps']} Mbps")

Cross-Launcher Testing
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.mindscope import (
       ClusterExperiment, MesoscopeExperiment, NeuropixelExperiment
   )

   # Test same workflow across all Mindscope rigs
   params_file = "shared_workflow_params.json"

   launchers = [
       ("Cluster", ClusterExperiment()),
       ("Mesoscope", MesoscopeExperiment()),
       ("Neuropixel", NeuropixelExperiment())
   ]

   results = {}
   for name, launcher in launchers:
       success = launcher.run(params_file)
       results[name] = {
           'success': success,
           'pickle_path': launcher.pickle_file_path if success else None,
           'summary': launcher.get_pickle_data_summary() if success else None
       }

   print("Cross-launcher compatibility test results:")
   for name, result in results.items():
       print(f"{name}: {'✅ Success' if result['success'] else '❌ Failed'}")

Key Methods
-----------

Common Methods (All Mindscope Launchers)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: openscope_experimental_launcher.mindscope.base.BaseMindscope.post_experiment_processing

   Performs Mindscope-specific post-processing including pickle metadata generation.

.. automethod:: openscope_experimental_launcher.mindscope.base.BaseMindscope.get_pickle_data_summary

   Returns a summary of the pickle metadata including rig-specific information.

.. automethod:: openscope_experimental_launcher.mindscope.base.BaseMindscope.create_pickle_metadata

   Creates rig-specific pickle metadata file with experiment information.

Rig-Specific Output Formats
----------------------------

Cluster Metadata
~~~~~~~~~~~~~~~~

.. code-block:: python

   # Cluster pickle metadata structure
   cluster_metadata = {
       'rig_type': 'cluster',
       'session_uuid': 'uuid-string',
       'mouse_id': 'cluster_mouse_001',
       'duration_seconds': 120.5,
       'num_parameters': 9,
       'cluster_node_info': 'compute-node-01',
       'job_queue_id': 'slurm-12345',
       'allocated_resources': {
           'cpu_cores': 8,
           'memory_gb': 32,
           'gpu_count': 1
       },
       'has_stdout': False,
       'has_stderr': False,
       'pickle_file_size_bytes': 2432
   }

Mesoscope Metadata
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Mesoscope pickle metadata structure
   mesoscope_metadata = {
       'rig_type': 'mesoscope',
       'session_uuid': 'uuid-string', 
       'mouse_id': 'mesoscope_mouse_001',
       'duration_seconds': 180.3,
       'num_parameters': 9,
       'num_imaging_planes': 4,
       'zoom_level': '2x',
       'frame_rate_hz': 30.0,
       'field_of_view_um': [800, 800],
       'imaging_depth_um': 200,
       'laser_power_mw': 15.0,
       'estimated_data_size_gb': 12.5,
       'has_stdout': False,
       'has_stderr': False,
       'pickle_file_size_bytes': 2565
   }

Neuropixel Metadata
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Neuropixel pickle metadata structure
   neuropixel_metadata = {
       'rig_type': 'neuropixel',
       'session_uuid': 'uuid-string',
       'mouse_id': 'neuropixel_mouse_001', 
       'duration_seconds': 240.1,
       'num_parameters': 9,
       'num_probes': 2,
       'num_recording_channels': 768,
       'sampling_rate_hz': 30000,
       'estimated_data_rate_mbps': 185.0,
       'probe_types': ['Neuropixels 1.0', 'Neuropixels 2.0'],
       'probe_configurations': [
           {
               'probe_id': 'probe_1',
               'insertion_depth_um': 3000,
               'brain_region': 'Visual Cortex'
           }
       ],
       'lfp_sampling_rate_hz': 2500,
       'has_stdout': False,
       'has_stderr': False,
       'pickle_file_size_bytes': 2594
   }

Parameter Configuration
-----------------------

Basic Mindscope Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~

All Mindscope launchers use the same basic parameter structure:

.. code-block:: json

   {
       "mouse_id": "mindscope_mouse_001",
       "user_id": "mindscope_researcher",
       "repository_url": "https://github.com/AllenNeuralDynamics/openscope-community-predictive-processing.git",
       "bonsai_path": "code/stimulus-control/src/Standard_oddball_slap2.bonsai",
       "output_directory": "C:/MindoscopeData"
   }

Rig-Specific Parameters
~~~~~~~~~~~~~~~~~~~~~~~

**Cluster Parameters:**

.. code-block:: json

   {
       "session_type": "cluster_computing",
       "rig_id": "cluster_rig_001",
       "compute_resources": {
           "requested_cores": 8,
           "requested_memory_gb": 32,
           "requested_gpu": true
       }
   }

**Mesoscope Parameters:**

.. code-block:: json

   {
       "session_type": "mesoscope_imaging",
       "rig_id": "mesoscope_rig_001",
       "imaging_config": {
           "zoom_level": "2x",
           "frame_rate_hz": 30.0,
           "num_planes": 4,
           "laser_power_mw": 15.0
       }
   }

**Neuropixel Parameters:**

.. code-block:: json

   {
       "session_type": "neuropixel_recording",
       "rig_id": "neuropixel_rig_001", 
       "recording_config": {
           "num_probes": 2,
           "sampling_rate_hz": 30000,
           "lfp_sampling_rate_hz": 2500,
           "probe_types": ["Neuropixels 1.0", "Neuropixels 2.0"]
       }
   }

Advanced Usage
--------------

Batch Processing
~~~~~~~~~~~~~~~~

.. code-block:: python

   def run_mindscope_batch(param_files, launcher_type='auto'):
       """Run multiple experiments in batch mode."""
       
       results = []
       
       for param_file in param_files:
           # Auto-select launcher based on parameters
           if launcher_type == 'auto':
               with open(param_file) as f:
                   params = json.load(f)
               
               rig_id = params.get('rig_id', '').lower()
               if 'cluster' in rig_id:
                   launcher = ClusterExperiment()
               elif 'mesoscope' in rig_id:
                   launcher = MesoscopeExperiment()
               elif 'neuropixel' in rig_id:
                   launcher = NeuropixelExperiment()
               else:
                   launcher = ClusterExperiment()  # Default
           else:
               launcher = launcher_type()
           
           # Run experiment
           success = launcher.run(param_file)
           
           results.append({
               'param_file': param_file,
               'launcher': type(launcher).__name__,
               'success': success,
               'pickle_metadata': launcher.pickle_file_path if success else None
           })
       
       return results

Metadata Analysis
~~~~~~~~~~~~~~~~~

.. code-block:: python

   def analyze_mindscope_session(pickle_metadata_path):
       """Analyze Mindscope pickle metadata."""
       
       import pickle
       
       with open(pickle_metadata_path, 'rb') as f:
           metadata = pickle.load(f)
       
       analysis = {
           'rig_type': metadata['rig_type'],
           'session_duration_minutes': metadata['duration_seconds'] / 60,
           'efficiency_score': calculate_efficiency(metadata),
           'data_quality_metrics': extract_quality_metrics(metadata)
       }
       
       return analysis

   def calculate_efficiency(metadata):
       """Calculate session efficiency based on rig type."""
       
       rig_type = metadata['rig_type']
       duration = metadata['duration_seconds']
       
       if rig_type == 'cluster':
           # Efficiency based on resource utilization
           return min(duration / 300, 1.0)  # Normalize to 5-minute sessions
       elif rig_type == 'mesoscope':
           # Efficiency based on imaging parameters
           frame_rate = metadata.get('frame_rate_hz', 30)
           return min(frame_rate / 30.0, 1.0)
       elif rig_type == 'neuropixel':
           # Efficiency based on channel utilization
           channels = metadata.get('num_recording_channels', 384)
           return min(channels / 384.0, 1.0)
       
       return 0.5  # Default efficiency

Custom Mindscope Launcher
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.mindscope.base import BaseMindscope

   class CustomMindscope(BaseMindscope):
       """Custom Mindscope launcher for specialized rig."""
       
       def __init__(self):
           super().__init__()
           self.rig_type = "custom"
       
       def create_rig_specific_metadata(self):
           """Override to add custom rig metadata."""
           custom_metadata = {
               'custom_hardware_version': '2.1.0',
               'custom_calibration_date': '2025-06-01',
               'custom_settings': self.params.get('custom_settings', {})
           }
           return custom_metadata
       
       def get_pickle_data_summary(self):
           """Override to add custom summary fields."""
           summary = super().get_pickle_data_summary()
           summary.update({
               'custom_metric': self.calculate_custom_metric(),
               'hardware_version': self.get_hardware_version()
           })
           return summary

Error Handling and Troubleshooting
-----------------------------------

Common Mindscope Errors
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def robust_mindscope_runner(params_file, launcher_class):
       """Run Mindscope experiment with comprehensive error handling."""
       
       try:
           experiment = launcher_class()
           success = experiment.run(params_file)
           
           if not success:
               # Check for common Mindscope issues
               if not experiment.pickle_file_path:
                   print("Error: Pickle metadata file was not created")
                   print("Check write permissions and disk space")
               
               # Analyze Bonsai errors
               bonsai_errors = experiment.get_bonsai_errors()
               if "property" in bonsai_errors.lower():
                   print("Warning: Bonsai property error detected")
                   print("This workflow may not support Mindscope parameters")
               
           return success
           
       except ImportError as e:
           print(f"Mindscope module import error: {e}")
           print("Ensure all Mindscope dependencies are installed")
           return False
           
       except Exception as e:
           print(f"Unexpected Mindscope error: {e}")
           return False

Pickle File Validation
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def validate_mindscope_pickle(pickle_path):
       """Validate Mindscope pickle metadata structure."""
       
       try:
           with open(pickle_path, 'rb') as f:
               metadata = pickle.load(f)
           
           # Check required fields
           required_fields = [
               'rig_type', 'session_uuid', 'mouse_id', 
               'duration_seconds', 'pickle_file_size_bytes'
           ]
           
           missing_fields = [field for field in required_fields 
                           if field not in metadata]
           
           if missing_fields:
               print(f"Missing required fields: {missing_fields}")
               return False
           
           # Validate rig-specific fields
           rig_type = metadata['rig_type']
           if rig_type == 'mesoscope':
               mesoscope_fields = ['num_imaging_planes', 'frame_rate_hz']
               missing_mesoscope = [field for field in mesoscope_fields 
                                  if field not in metadata]
               if missing_mesoscope:
                   print(f"Missing mesoscope fields: {missing_mesoscope}")
                   return False
           
           print("Pickle metadata validation passed")
           return True
           
       except Exception as e:
           print(f"Pickle validation error: {e}")
           return False

Integration Examples
--------------------

Data Pipeline Integration
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def mindscope_to_data_pipeline(pickle_metadata_path):
       """Convert Mindscope metadata to data pipeline format."""
       
       with open(pickle_metadata_path, 'rb') as f:
           metadata = pickle.load(f)
       
       # Convert to standard pipeline format
       pipeline_metadata = {
           'experiment_id': metadata['session_uuid'],
           'subject_id': metadata['mouse_id'],
           'rig_type': metadata['rig_type'],
           'duration_seconds': metadata['duration_seconds'],
           'data_streams': []
       }
       
       # Add rig-specific data streams
       if metadata['rig_type'] == 'mesoscope':
           pipeline_metadata['data_streams'].append({
               'stream_type': 'imaging',
               'frame_rate_hz': metadata.get('frame_rate_hz'),
               'num_planes': metadata.get('num_imaging_planes')
           })
       elif metadata['rig_type'] == 'neuropixel':
           pipeline_metadata['data_streams'].append({
               'stream_type': 'electrophysiology',
               'sampling_rate_hz': metadata.get('sampling_rate_hz'),
               'num_channels': metadata.get('num_recording_channels')
           })
       
       return pipeline_metadata