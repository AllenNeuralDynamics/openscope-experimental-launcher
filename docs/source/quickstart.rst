Quick Start Guide
=================

This guide will help you run your first experiment with the OpenScope Experimental Launcher.

Configuration Overview
----------------------

The launcher uses a **three-tier configuration system**:

- **Rig Config** (TOML): Hardware constants (rig_id, data paths)
- **Parameter Files** (JSON): Experiment settings (subject_id, protocols)  
- **Runtime Prompts**: Interactive collection of missing values

**Priority**: Runtime Prompts > JSON Parameters > Rig Config

.. tip::
   **First Time Setup**: The launcher automatically creates a default rig configuration 
   file on first run. The rig_id defaults to your computer's hostname.

For complete details, see :doc:`configuration`.

Basic Experiment Setup
-----------------------

1. **Create a Parameter File**   Create a JSON file with your experiment parameters:

   .. code-block:: json
      :caption: example_params.json

      {
          "subject_id": "test_mouse_001",
          "user_id": "researcher_name",
          "repository_url": "https://github.com/AllenNeuralDynamics/openscope-community-predictive-processing.git",
          "repository_commit_hash": "main",
          "local_repository_path": "C:/BonsaiExperiments",
          "script_path": "code/stimulus-control/src/predictive_processing_workflow.bonsai",
          "bonsai_exe_path": "code/stimulus-control/bonsai/Bonsai.exe",
          "output_root_folder": "C:/experiment_data",
          "collect_mouse_runtime_data": true,
          "protocol_id": ["protocol_001"]
      }

2. **Choose Your Interface**

   Select the appropriate launcher for your experiment type:   **For Bonsai Workflows:**

   .. code-block:: python

      from openscope_experimental_launcher.launchers import BonsaiLauncher

      # Create launcher instance
      launcher = BonsaiLauncher()

      # Initialize with parameter file (uses default rig config)
      launcher.initialize_launcher(param_file="example_params.json")
      
      # Run the experiment
      success = launcher.run("example_params.json")
      if success:
          print("Experiment completed successfully!")
          print(f"Data saved to: {launcher.output_session_folder}")
      else:
          print("Experiment failed. Check logs for details.")   .. note::
      For testing, you can specify a custom rig config path, but this is rarely needed:
      
      .. code-block:: python
      
         launcher.initialize_launcher(param_file="test.json", rig_config_path="/custom/path")

   **For MATLAB Scripts:**

   .. code-block:: python

      from openscope_experimental_launcher.launchers import MatlabLauncher

      # Create launcher instance  
      launcher = MatlabLauncher()

      # Initialize and run the experiment
      launcher.initialize_launcher(param_file="matlab_params.json")
      success = launcher.run("matlab_params.json")   **For Python Scripts:**

   .. code-block:: python

      from openscope_experimental_launcher.launchers import PythonLauncher

      # Create launcher instance
      launcher = PythonLauncher()

      # Initialize and run the experiment
      launcher.initialize_launcher(param_file="python_params.json")
      success = launcher.run("python_params.json")

3. **Using Project Scripts**   For project-specific experiments, use the launcher scripts:

   .. code-block:: bash

      # Test BaseLauncher functionality
      python scripts/minimalist_launcher.py scripts/example_minimalist_params.json

      # Predictive processing experiments  
      python scripts/predictive_processing_launcher.py path/to/pp_params.json

Command Line Usage
------------------

You can also run experiments directly from the command line:

.. code-block:: bash

   # Run with parameter file
   python -m openscope_experimental_launcher.base.experiment example_params.json

   # Run Predictive Processing experiment
   python scripts/predictive_processing_launcher.py pp_params.json

Runtime Data Collection (Optional)
----------------------------------

The launcher supports interactive data collection at runtime. When ``collect_mouse_runtime_data: true`` is set in your parameter file:

- **Protocol Confirmation**: Confirms protocol and platform settings before starting
- **Animal Weight Collection**: Prompts for pre- and post-experiment animal weights
- **Simple Interface**: Press Enter to keep existing values, or type new values to change them

All runtime data is automatically included in the generated ``session.json`` file. This feature is completely optional and experiments will run normally without it.

Predictive Processing Experiments
----------------------------------

The launcher includes specialized support for Predictive Processing experiments with automatic post-processing:

.. code-block:: python

   from openscope_experimental_launcher.launchers import PredictiveProcessingLauncher

   # Create experiment with automatic post-processing
   launcher = PredictiveProcessingLauncher(param_file="pp_params.json")
   success = launcher.run()
   
   # Check generated outputs
   if success:
       print(f"Experiment data: {launcher.output_session_folder}")
       print(f"Stimulus table: {launcher.output_session_folder}/stimulus_table_output/")
       
**Post-Processing Features:**
   - Automatic conversion of orientation data to stimulus tables
   - Integration with Harp timing data for precise synchronization
   - Comprehensive validation and error reporting
   - Detailed conversion statistics

Next Steps
----------

- Learn about :doc:`parameter_files` for advanced configuration
- Explore :doc:`rig_launchers` for rig-specific features
- See :doc:`examples` for complete working examples
- Check the :doc:`api/base` for detailed API documentation