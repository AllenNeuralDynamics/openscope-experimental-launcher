Rig Launchers
=============

The OpenScope Experimental Launcher provides specialized launchers for different experimental rig types. Each launcher extends the base functionality with rig-specific features and metadata generation.

Overview
--------

.. list-table:: Launcher Comparison
   :header-rows: 1
   :widths: 20 25 25 30

   * - Launcher
     - Use Case
     - Output Files
     - Special Features
   * - BaseExperiment
     - Generic Bonsai workflows
     - .pkl session file
     - Basic process management
   * - SLAP2Experiment
     - SLAP2 imaging experiments
     - .pkl, stimulus table .csv, session .json
     - AIND metadata, stimulus analysis
   * - ClusterExperiment
     - Cluster rig experiments
     - .pkl, cluster metadata .pkl
     - Cluster-specific metadata
   * - MesoscopeExperiment
     - Mesoscope imaging
     - .pkl, mesoscope metadata .pkl
     - Imaging plane tracking
   * - NeuropixelExperiment
     - Electrophysiology recording
     - .pkl, neuropixel metadata .pkl
     - Probe configuration tracking

Base Experiment Launcher
-------------------------

The foundation for all other launchers, providing core Bonsai process management.

.. code-block:: python

   from openscope_experimental_launcher.base.experiment import BaseExperiment

   experiment = BaseExperiment()
   success = experiment.run("parameters.json")

**Features:**
- Bonsai process management with Windows job objects
- Git repository cloning and management
- Session UUID generation and tracking
- Memory monitoring and process cleanup
- Basic parameter validation

**Output:**
- Session .pkl file with basic experiment metadata

SLAP2 Experiment Launcher
--------------------------

Specialized launcher for Selective Plane Activation with Multiphoton microscopy (SLAP2) experiments.

.. code-block:: python

   from openscope_experimental_launcher.slap2.launcher import SLAP2Experiment

   experiment = SLAP2Experiment()
   success = experiment.run("slap2_parameters.json")

   if success:
       print(f"Stimulus table: {experiment.stimulus_table_path}")
       print(f"Session metadata: {experiment.session_json_path}")

**Enhanced Features:**
- AIND-data-schema compliant session.json generation
- Automatic stimulus table creation from trial data
- SLAP field-of-view (FOV) configuration tracking
- Laser parameter validation and logging
- Stimulus-only metadata mode (no POPhys requirements)

**Output Files:**
- Session .pkl file (basic experiment data)
- Stimulus table .csv file (trial-by-trial stimulus information)
- Session .json file (AIND-compliant metadata)

**SLAP2-Specific Parameters:**

.. code-block:: json

   {
       "session_type": "SLAP2",
       "experimenter_name": "Dr. Researcher",
       "laser_power": 15.0,
       "laser_wavelength": 920,
       "num_trials": 200,
       "slap_fovs": [
           {
               "index": 0,
               "imaging_depth": 150,
               "targeted_structure": "V1",
               "fov_coordinate_ml": 2.5,
               "fov_coordinate_ap": -2.0,
               "frame_rate": 30.0
           }
       ]   }

Cross-Launcher Compatibility
----------------------------

One of the key features of the system is that the same Bonsai workflow can run across different rig types with their respective post-processing.

.. code-block:: python

   # Same parameter file, different launchers
   params_file = "shared_workflow_params.json"

   # Base launcher - minimal output
   base_exp = BaseExperiment()
   base_exp.run(params_file)

   # SLAP2 launcher - adds stimulus table and session.json
   slap2_exp = SLAP2Experiment()
   slap2_exp.run(params_file)

**Benefits:**
- Workflow portability across rig types
- Consistent parameter structure
- Rig-specific metadata without workflow changes
- Easy migration between experimental setups

Launcher Selection Guide
------------------------

Choose the appropriate launcher based on your experimental setup:

**Use BaseExperiment when:**
- Running generic Bonsai workflows
- No rig-specific metadata needed
- Prototyping or testing workflows
- Simple stimulus presentation experiments

**Use SLAP2Experiment when:**
- Running SLAP2 imaging experiments
- Need AIND-compliant metadata
- Require stimulus table generation
- Want comprehensive session documentation

Custom Launcher Development
---------------------------

You can create custom launchers by extending the base classes:

.. code-block:: python

   from openscope_experimental_launcher.base.experiment import BaseExperiment

   class CustomRigExperiment(BaseExperiment):
       """Custom launcher for specialized rig."""
       
       def __init__(self):
           super().__init__()
           self.custom_metadata = {}
       
       def post_experiment_processing(self) -> bool:
           """Add custom post-processing logic."""
           # Generate custom metadata files
           self._create_custom_metadata()
           return super().post_experiment_processing()
       
       def _create_custom_metadata(self):
           """Create rig-specific metadata files."""
           # Implementation specific to your rig
           pass

**Custom Launcher Guidelines:**
- Always call ``super().__init__()`` in ``__init__``
- Override ``post_experiment_processing()`` for custom outputs
- Maintain compatibility with base parameter structure
- Add rig-specific parameters as needed
- Include comprehensive logging

Advanced Usage
--------------

Launcher Chaining
~~~~~~~~~~~~~~~~~

Run multiple launchers in sequence for comprehensive output:

.. code-block:: python

   def run_comprehensive_experiment(params_file):
       """Run experiment with multiple output formats."""
       
       # Run SLAP2 for AIND metadata
       slap2_exp = SLAP2Experiment()
       slap2_success = slap2_exp.run(params_file)
       
       if slap2_success:
           # Run cluster for additional metadata
           cluster_exp = ClusterExperiment()
           cluster_exp.run(params_file)
           
           return {
               'session_json': slap2_exp.session_json_path,
               'stimulus_table': slap2_exp.stimulus_table_path,
               'cluster_metadata': cluster_exp.pickle_file_path
           }

Conditional Launcher Selection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Automatically select launcher based on parameters:

.. code-block:: python

   def auto_select_launcher(params_file):
       """Automatically select appropriate launcher."""
       
       with open(params_file) as f:
           params = json.load(f)
       
       rig_type = params.get('rig_id', '').lower()
       session_type = params.get('session_type', '').lower()
         if 'slap2' in rig_type or 'slap2' in session_type:
           return SLAP2Experiment()
       else:
           return BaseExperiment()

Performance Considerations
--------------------------

**Memory Usage:**
- All launchers include memory monitoring
- Automatic cleanup of runaway processes
- Windows job object process management

**File I/O:**
- Efficient pickle serialization for metadata
- Streaming CSV generation for large stimulus tables
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