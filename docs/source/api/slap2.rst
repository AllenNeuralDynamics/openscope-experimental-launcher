API Reference - SLAP2 Module
=============================

The SLAP2 module provides specialized functionality for Selective Plane Activation with Multiphoton microscopy experiments.

SLAP2Experiment Class
---------------------

.. autoclass:: openscope_experimental_launcher.slap2.launcher.SLAP2Experiment
   :members:
   :undoc-members:
   :show-inheritance:

   Specialized launcher for SLAP2 imaging experiments with enhanced metadata generation.

   **Enhanced Features:**
   
   - AIND-data-schema compliant session.json generation
   - Automatic stimulus table creation from trial data
   - SLAP field-of-view (FOV) configuration tracking
   - Stimulus-only metadata mode (no POPhys requirements)

   **Output Files:**
   
   - Session .pkl file (basic experiment data)
   - Stimulus table .csv file (trial-by-trial stimulus information)
   - Session .json file (AIND-compliant metadata)

Key Methods
-----------

.. automethod:: openscope_experimental_launcher.slap2.launcher.SLAP2Experiment.post_experiment_processing

   Performs SLAP2-specific post-processing including stimulus table and session metadata generation.

.. automethod:: openscope_experimental_launcher.slap2.launcher.SLAP2Experiment.create_stimulus_table

   Creates a comprehensive stimulus table from experimental data.

.. automethod:: openscope_experimental_launcher.slap2.launcher.SLAP2Experiment.create_session_json

   Generates AIND-compliant session metadata in JSON format.

Example Usage
-------------

Basic SLAP2 Experiment
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.slap2.launcher import SLAP2Experiment
   import logging

   # Set up logging
   logging.basicConfig(level=logging.INFO)

   # Create SLAP2 experiment
   experiment = SLAP2Experiment()

   # Run with SLAP2 parameters
   success = experiment.run("slap2_params.json")

   if success:
       print(f"SLAP2 experiment completed successfully!")       print(f"Session data: {experiment.session_directory}")
       print(f"Stimulus table: {experiment.stimulus_table_path}")
       print(f"Session metadata: {experiment.session_json_path}")
   else:
       print("SLAP2 experiment failed. Check logs for details.")

SLAP2 Parameter File
~~~~~~~~~~~~~~~~~~~~

.. code-block:: json

   {
       "subject_id": "slap2_mouse_001",
       "user_id": "imaging_researcher",
       "repository_url": "https://github.com/AllenNeuralDynamics/openscope-community-predictive-processing.git",
       "bonsai_path": "code/stimulus-control/src/Standard_oddball_slap2.bonsai",
       "session_type": "SLAP2",
       "rig_id": "slap2_rig_001",
       "user_id": "Dr. Jane Smith",
       "laser_power": 12.5,
       "laser_wavelength": 920,
       "num_trials": 500,
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
           }
       ]
   }

Accessing SLAP2 Outputs
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   experiment = SLAP2Experiment()
   success = experiment.run("slap2_params.json")

   if success:
       # Read stimulus table
       import pandas as pd
       stimulus_table = pd.read_csv(experiment.stimulus_table_path)
       print(f"Stimulus table shape: {stimulus_table.shape}")
       print(f"Stimulus columns: {list(stimulus_table.columns)}")
       
       # Read session metadata
       import json
       with open(experiment.session_json_path) as f:
           session_metadata = json.load(f)
       
       print(f"Session type: {session_metadata['session_type']}")
       print(f"Number of stimulus epochs: {len(session_metadata['stimulus_epochs'])}")

SLAP2-Specific Features
-----------------------

Field of View (FOV) Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

SLAP2 experiments support multiple imaging planes with detailed configuration:

.. code-block:: python

   slap_fovs = [
       {
           "index": 0,
           "imaging_depth": 150,
           "targeted_structure": "Layer 2/3 Visual Cortex",
           "fov_coordinate_ml": 2.5,
           "fov_coordinate_ap": -2.0,
           "fov_reference": "Bregma",
           "fov_width": 512,
           "fov_height": 512,
           "magnification": "40x",
           "frame_rate": 30.0,
           "session_type": "Parent"
       },
       {
           "index": 1,
           "imaging_depth": 300,
           "targeted_structure": "Layer 5 Visual Cortex", 
           "fov_coordinate_ml": 2.5,
           "fov_coordinate_ap": -2.0,
           "fov_reference": "Bregma",
           "fov_width": 256,
           "fov_height": 256,
           "magnification": "60x",
           "frame_rate": 15.0,
           "session_type": "Child"
       }
   ]

Laser Parameter Validation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # SLAP2 validates laser parameters
   laser_config = {
       "laser_power": 12.5,        # Power in mW
       "laser_wavelength": 920,    # Wavelength in nm
       "laser_pulse_width": 100    # Pulse width in fs (optional)
   }

Stimulus-Only Mode
~~~~~~~~~~~~~~~~~~

SLAP2 can generate metadata without requiring optical physiology data streams:

.. code-block:: python

   # Parameters for stimulus-only session
   stimulus_only_params = {
       "subject_id": "stimulus_test",
       "user_id": "researcher",
       "repository_url": "https://github.com/user/repo.git",
       "bonsai_path": "stimulus_workflow.bonsai",
       "session_type": "stimulus_presentation",
       "num_trials": 100
   }

   experiment = SLAP2Experiment()
   success = experiment.run(stimulus_only_params)

   # Generates complete stimulus metadata without POPhys requirements

AIND Data Schema Integration
----------------------------

Session Metadata Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The generated session.json follows AIND data schema standards:

.. code-block:: json

   {
       "describedBy": "https://raw.githubusercontent.com/AllenInstitute/aind-data-schema/main/src/aind_data_schema/core/session.py",
       "schema_version": "0.3.0",
       "session_start_time": "2025-06-13T10:30:00.000000",
       "session_end_time": "2025-06-13T10:38:30.000000",
       "experimenter_full_name": ["Dr. Jane Smith"],
       "session_type": "SLAP2",
       "rig_id": "slap2_rig_001",
       "subject_id": "slap2_mouse_001",
       "stimulus_epochs": [
           {
               "stimulus_name": "SLAP2 Oddball Stimulus",
               "stimulus_modalities": ["Visual"],
               "stimulus_parameters": {},
               "software": [
                   {
                       "name": "Bonsai",
                       "version": "2.8.0",
                       "url": "https://github.com/AllenNeuralDynamics/openscope-community-predictive-processing.git"
                   }
               ]
           }
       ],
       "data_streams": []
   }

Stimulus Table Format
~~~~~~~~~~~~~~~~~~~~~

The generated stimulus table includes comprehensive trial information:

.. csv-table:: Stimulus Table Example
   :header: "trial_index", "start_time", "stop_time", "stimulus_name", "stimulus_type", "duration"
   :widths: 10, 15, 15, 20, 15, 10

   "0", "0.000", "2.000", "oddball_stimulus", "visual", "2.0"
   "1", "3.000", "5.000", "oddball_stimulus", "visual", "2.0" 
   "2", "6.000", "8.000", "oddball_stimulus", "visual", "2.0"

Validation and Error Handling
------------------------------

SLAP2 Parameter Validation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def validate_slap2_parameters(params):
       """Validate SLAP2-specific parameters."""
       
       # Check required SLAP2 fields
       required_slap2_fields = [
           'laser_power', 'laser_wavelength', 'slap_fovs'
       ]
       
       for field in required_slap2_fields:
           if field not in params:
               raise ValueError(f"Missing required SLAP2 parameter: {field}")
       
       # Validate laser power range
       laser_power = params['laser_power']
       if not (0 < laser_power <= 50):
           raise ValueError("Laser power must be between 0 and 50 mW")
       
       # Validate FOV configuration
       fovs = params['slap_fovs']
       if not isinstance(fovs, list) or len(fovs) == 0:
           raise ValueError("slap_fovs must be a non-empty list")
       
       for fov in fovs:
           required_fov_fields = [
               'index', 'imaging_depth', 'targeted_structure'
           ]
           for field in required_fov_fields:
               if field not in fov:
                   raise ValueError(f"Missing FOV field: {field}")

Common SLAP2 Errors
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Handle common SLAP2 errors
   try:
       experiment = SLAP2Experiment()
       success = experiment.run("slap2_params.json")
       
   except ValueError as e:
       if "laser_power" in str(e):
           print("Laser power configuration error")
       elif "slap_fovs" in str(e):
           print("FOV configuration error")
       else:
           print(f"Parameter validation error: {e}")
           
   except FileNotFoundError as e:
       print(f"Output file creation failed: {e}")
       # Check write permissions and disk space
       
   except Exception as e:
       print(f"Unexpected SLAP2 error: {e}")

Advanced SLAP2 Usage
--------------------

Multi-Session Experiments
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def run_slap2_session_series(base_params, session_configs):
       """Run a series of SLAP2 sessions with different configurations."""
       
       results = []
       
       for i, config in enumerate(session_configs):
           # Update parameters for this session
           session_params = base_params.copy()
           session_params.update(config)
           session_params['subject_id'] = f"{base_params['subject_id']}_session_{i}"
           
           # Run session
           experiment = SLAP2Experiment()
           success = experiment.run(session_params)
           
           results.append({
               'session_index': i,
               'success': success,
               'output_directory': experiment.session_directory if success else None,
               'stimulus_table': experiment.stimulus_table_path if success else None,
               'session_metadata': experiment.session_json_path if success else None
           })
       
       return results

Custom Stimulus Analysis
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def analyze_slap2_stimulus_table(stimulus_table_path):
       """Analyze SLAP2 stimulus table for timing and trial statistics."""
       
       import pandas as pd
       import numpy as np
       
       # Load stimulus table
       df = pd.read_csv(stimulus_table_path)
       
       # Calculate timing statistics
       trial_durations = df['stop_time'] - df['start_time']
       inter_trial_intervals = df['start_time'].diff().dropna()
       
       analysis = {
           'total_trials': len(df),
           'total_duration': df['stop_time'].max(),
           'mean_trial_duration': trial_durations.mean(),
           'std_trial_duration': trial_durations.std(),
           'mean_iti': inter_trial_intervals.mean(),
           'std_iti': inter_trial_intervals.std(),
           'stimulus_types': df['stimulus_type'].value_counts().to_dict()
       }
       
       return analysis

Integration with Analysis Pipelines
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def slap2_to_analysis_pipeline(experiment_output):
       """Convert SLAP2 outputs to analysis pipeline format."""
       
       # Load SLAP2 outputs
       with open(experiment_output['session_metadata']) as f:
           session_data = json.load(f)
       
       stimulus_table = pd.read_csv(experiment_output['stimulus_table'])
       
       # Convert to analysis format
       analysis_input = {
           'session_uuid': session_data.get('session_uuid'),
           'subject_id': session_data.get('subject_id'),
           'session_start': session_data.get('session_start_time'),
           'stimulus_times': stimulus_table[['start_time', 'stop_time']].values,
           'stimulus_types': stimulus_table['stimulus_type'].values,
           'imaging_metadata': {
               'laser_power': session_data.get('laser_power'),
               'laser_wavelength': session_data.get('laser_wavelength'),
               'fovs': session_data.get('slap_fovs', [])
           }
       }
       
       return analysis_input