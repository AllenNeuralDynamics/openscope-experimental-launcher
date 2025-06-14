Quick Start Guide
=================

This guide will help you run your first experiment with the OpenScope Experimental Launcher.

Basic Experiment Setup
-----------------------

1. **Create a Parameter File**

   Create a JSON file with your experiment parameters:

   .. code-block:: json
      :caption: example_params.json

      {
          "mouse_id": "test_mouse_001",
          "user_id": "researcher_name",
          "repository_url": "https://github.com/AllenNeuralDynamics/openscope-community-predictive-processing.git",
          "repository_commit_hash": "main",
          "local_repository_path": "C:/BonsaiExperiments",
          "bonsai_path": "code/stimulus-control/src/Standard_oddball_slap2.bonsai",
          "bonsai_exe_path": "code/stimulus-control/bonsai/Bonsai.exe",
          "output_directory": "C:/experiment_data"
      }

2. **Run Basic Experiment**

   .. code-block:: python

      from openscope_experimental_launcher.base.experiment import BaseExperiment

      # Create experiment instance
      experiment = BaseExperiment()

      # Run the experiment
      success = experiment.run("example_params.json")

      if success:
          print("Experiment completed successfully!")
          print(f"Data saved to: {experiment.session_output_path}")
      else:
          print("Experiment failed. Check logs for details.")

Command Line Usage
------------------

You can also run experiments directly from the command line:

.. code-block:: bash

   # Run with parameter file
   python -m openscope_experimental_launcher.base.experiment example_params.json

   # Run SLAP2 experiment
   python -m openscope_experimental_launcher.slap2.launcher slap2_params.json

Rig-Specific Launchers
----------------------

SLAP2 Imaging Experiments
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.slap2.launcher import SLAP2Experiment

   # Create SLAP2 experiment with enhanced metadata generation
   experiment = SLAP2Experiment()
   success = experiment.run("slap2_params.json")

   # Check generated outputs
   if success:
       print(f"Experiment data: {experiment.session_output_path}")
       print(f"Stimulus table: {experiment.stimulus_table_path}")
       print(f"Session metadata: {experiment.session_json_path}")

Mindscope Experiments
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.mindscope import (
       ClusterExperiment, 
       MesoscopeExperiment, 
       NeuropixelExperiment
   )

   # Choose the appropriate launcher for your rig
   experiment = MesoscopeExperiment()  # or ClusterExperiment(), NeuropixelExperiment()
   success = experiment.run("mindscope_params.json")

   # Check rig-specific outputs
   if success:
       print(f"Pickle metadata: {experiment.pickle_file_path}")
       summary = experiment.get_pickle_data_summary()
       print(f"Data summary: {summary}")

Working with Sessions
---------------------

Each experiment generates a unique session with comprehensive tracking:

.. code-block:: python

   # Session information is automatically generated
   print(f"Session UUID: {experiment.session_uuid}")
   print(f"Mouse ID: {experiment.mouse_id}")
   print(f"User ID: {experiment.user_id}")
   print(f"Start time: {experiment.start_time}")
   print(f"Duration: {experiment.stop_time - experiment.start_time}")

   # Access experiment metadata
   print(f"Parameter checksum: {experiment.params_checksum}")
   print(f"Workflow checksum: {experiment.script_checksum}")

Real-time Monitoring
--------------------

Monitor experiment progress in real-time:

.. code-block:: python

   import logging

   # Set up logging to see real-time updates
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(levelname)s - %(message)s'
   )

   # Run experiment with detailed logging
   experiment = BaseExperiment()
   success = experiment.run("params.json")

Parameter Validation
--------------------

The launcher validates parameters before running:

.. code-block:: python

   # Required parameters
   required_params = [
       "repository_url",
       "bonsai_path",
       "mouse_id",
       "user_id"
   ]

   # Optional parameters with defaults
   optional_params = {
       "output_directory": "data",
       "repository_commit_hash": "main",
       "local_repository_path": "C:/BonsaiTemp"
   }

Error Handling
--------------

Robust error handling and cleanup:

.. code-block:: python

   try:
       experiment = BaseExperiment()
       success = experiment.run("params.json")
       
       if not success:
           # Check Bonsai output for errors
           errors = experiment.get_bonsai_errors()
           print(f"Bonsai errors: {errors}")
           
   except Exception as e:
       print(f"Experiment failed: {e}")
       
   finally:
       # Cleanup is automatic, but you can force it
       experiment.stop()

Integration Testing
-------------------

Test that different rig launchers work with the same Bonsai workflow:

.. code-block:: python

   # Test cross-launcher compatibility
   from openscope_experimental_launcher.slap2.launcher import SLAP2Experiment
   from openscope_experimental_launcher.mindscope import ClusterExperiment

   # Same parameters, different launchers
   params_file = "shared_params.json"

   # Test SLAP2 launcher
   slap2_exp = SLAP2Experiment()
   slap2_success = slap2_exp.run(params_file)

   # Test Cluster launcher  
   cluster_exp = ClusterExperiment()
   cluster_success = cluster_exp.run(params_file)

   print(f"Same workflow ran on both rigs: {slap2_success and cluster_success}")

Next Steps
----------

- Learn about :doc:`parameter_files` for advanced configuration
- Explore :doc:`rig_launchers` for rig-specific features
- See :doc:`examples` for complete working examples
- Check the :doc:`api/base` for detailed API documentation