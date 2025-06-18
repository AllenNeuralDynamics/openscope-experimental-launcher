Parameter Files
===============

Parameter files are JSON configuration files that define how experiments are run. They specify repository locations, rig-specific settings and Bonsai parameters. Key subject and experimenter information is now collected interactively at runtime.

Basic Parameter Structure
-------------------------

.. code-block:: json
   :caption: Basic parameter file structure

   {
       "repository_url": "https://github.com/user/repo.git",
       "bonsai_path": "path/to/workflow.bonsai",
       "OutputFolder": "C:/experiment_data"
   }

Required Parameters
-------------------

These parameters must be present in every parameter file:

**repository_url** (string)
   Git repository URL containing the Bonsai workflow

**bonsai_path** (string)
   Relative path to the Bonsai workflow file within the repository

Runtime Information Collection
-----------------------------

The following information is collected interactively when you run an experiment:

**subject_id** (string)
   Unique identifier for the experimental subject (collected at runtime)

**user_id** (string)  
   Identifier for the person running the experiment (collected at runtime)

For SLAP2 experiments, additional information is collected:

**rig_id** (string)
   Identifier for the experimental rig (collected at runtime for SLAP2, with default shown)

Optional Parameters
-------------------

**repository_commit_hash** (string, default: "main")
   Specific commit, branch, or tag to checkout

**local_repository_path** (string, default: "C:/BonsaiTemp")
   Local directory for cloning the repository

**bonsai_exe_path** (string, default: "Bonsai.exe")
   Path to Bonsai executable within the repository

**OutputFolder** (string, default: "data")
   Directory for saving experiment output files

**session_type** (string, default: "experiment")
   Type of experimental session

**rig_id** (string, default: hostname)
   Identifier for the experimental rig

Bonsai Parameters
-----------------

Pass parameters directly to Bonsai workflows using the ``bonsai_parameters`` section:

.. code-block:: json

   {
       "subject_id": "test_mouse",
       "user_id": "researcher",
       "repository_url": "https://github.com/user/repo.git",
       "bonsai_path": "workflow.bonsai",
       "bonsai_parameters": {
           "NumTrials": 100,
           "StimulusDuration": 5.0,
           "InterTrialInterval": 2.0,
           "RewardSize": 0.01
       }
   }

.. note::
   Only parameters explicitly defined in the Bonsai workflow will be accepted. Unknown parameters will cause the workflow to fail.

Rig-Specific Parameters
-----------------------

SLAP2 Parameters
~~~~~~~~~~~~~~~~

SLAP2 experiments support additional imaging-specific parameters:

.. code-block:: json

   {
       "subject_id": "slap2_mouse_001",
       "user_id": "imaging_researcher",
       "repository_url": "https://github.com/AllenNeuralDynamics/repo.git",
       "bonsai_path": "imaging/slap2_workflow.bonsai",
       "session_type": "SLAP2",
       "rig_id": "slap2_rig_1",
       "user_id": "Dr. Researcher Name",
       "slap_fovs": [
           {
               "index": 0,
               "imaging_depth": 150,
               "targeted_structure": "V1",
               "fov_coordinate_ml": 2.5,
               "fov_coordinate_ap": -2.0,
               "fov_reference": "Bregma",
               "fov_width": 512,
               "fov_height": 512,
               "magnification": "40x",
               "frame_rate": 30.0
           }
       ],
       "laser_power": 15.0,
       "laser_wavelength": 920,
       "num_trials": 200
   }

Configuration File Integration
------------------------------

The launcher can also load settings from CamStim-style configuration files:

.. code-block:: json

   {
       "subject_id": "config_mouse",
       "user_id": "config_user",
       "repository_url": "https://github.com/user/repo.git", 
       "bonsai_path": "workflow.bonsai",
       "config_file_path": "C:/ProgramData/AIBS_MPE/camstim/config/stim.cfg"
   }

Parameter Validation
--------------------

The launcher performs validation on all parameters:

**Type Checking**
   Ensures parameters have the correct data types

**Required Field Validation**  
   Verifies all required parameters are present

**Path Validation**
   Checks that file and directory paths exist

**Repository Validation**
   Validates Git repository URLs and accessibility

**Bonsai Parameter Validation**
   Confirms Bonsai parameters match workflow expectations

Example Parameter Files
-----------------------

Minimal Example
~~~~~~~~~~~~~~~

.. code-block:: json
   :caption: minimal_params.json

   {
       "subject_id": "test_mouse",
       "user_id": "test_user",
       "repository_url": "https://github.com/AllenNeuralDynamics/openscope-community-predictive-processing.git",
       "bonsai_path": "code/stimulus-control/src/Standard_oddball_slap2.bonsai"
   }

Full SLAP2 Example
~~~~~~~~~~~~~~~~~~

.. code-block:: json
   :caption: full_slap2_params.json

   {
       "subject_id": "slap2_experimental_mouse",
       "user_id": "imaging_scientist",
       "repository_url": "https://github.com/AllenNeuralDynamics/openscope-community-predictive-processing.git",
       "repository_commit_hash": "v1.2.0",
       "local_repository_path": "C:/BonsaiExperiments/PredictiveProcessing",
       "bonsai_path": "code/stimulus-control/src/Standard_oddball_slap2.bonsai",
       "bonsai_exe_path": "code/stimulus-control/bonsai/Bonsai.exe",
       "output_directory": "C:/ExperimentData/SLAP2",
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
       ],
       "bonsai_parameters": {
           "TrialDuration": 8.0,
           "BaselineTime": 1.0,
           "StimulusTime": 2.0
       }
   }

Cross-Rig Compatibility
-----------------------

The same parameter file can often be used across different rig types:

.. code-block:: json
   :caption: cross_rig_params.json

   {
       "subject_id": "multi_rig_mouse",
       "user_id": "cross_platform_researcher",
       "repository_url": "https://github.com/AllenNeuralDynamics/openscope-community-predictive-processing.git",
       "bonsai_path": "code/stimulus-control/src/Standard_oddball_slap2.bonsai",
       "output_directory": "C:/SharedExperiments"
   }

This file can be used with:

.. code-block:: python   # Works with any launcher
   from openscope_experimental_launcher.base.experiment import BaseExperiment
   from openscope_experimental_launcher.slap2.launcher import SLAP2Experiment

   params = "cross_rig_params.json"
   
   # All these will work with the same parameter file
   BaseExperiment().run(params)
   SLAP2Experiment().run(params)  # Adds stimulus table + session.json

Best Practices
--------------

1. **Use Descriptive Names**
   
   .. code-block:: json
   
      {
          "subject_id": "VISp_ChR2_mouse_001_20250613",
          "user_id": "jane_smith_imaging_lab"
      }

2. **Include Experiment Context**
   
   .. code-block:: json
   
      {
          "session_type": "oddball_stimulus_SLAP2_imaging",
          "rig_id": "slap2_rig_behavior_room_2"
      }

3. **Version Control Integration**
   
   .. code-block:: json
   
      {
          "repository_commit_hash": "v2.1.3",
          "experiment_version": "predictive_processing_pilot_v1"
      }

4. **Absolute Paths for Clarity**
   
   .. code-block:: json
   
      {
          "output_directory": "C:/ExperimentData/2025/June/SLAP2_Sessions",
          "local_repository_path": "C:/BonsaiWorkflows/PredictiveProcessing"
      }

Common Errors
-------------

**Missing Required Parameters**

.. code-block:: json
   :caption: ❌ This will fail

   {
       "subject_id": "test_mouse"
       // Missing user_id, repository_url, bonsai_path
   }

**Invalid Bonsai Parameters**

.. code-block:: json
   :caption: ❌ This will fail if OutputDirectory is not defined in the workflow

   {
       "subject_id": "test_mouse",
       "user_id": "test_user", 
       "repository_url": "https://github.com/user/repo.git",
       "bonsai_path": "workflow.bonsai",
       "bonsai_parameters": {
           "OutputDirectory": "C:/Data"  // Only works if workflow has this property
       }
   }

**Incorrect File Paths**

.. code-block:: json
   :caption: ❌ This will fail

   {
       "bonsai_path": "nonexistent/workflow.bonsai",
       "output_directory": "Z:/invalid/drive"
   }

Parameter Schema Reference
--------------------------

For a complete schema definition, see the :doc:`api/base` documentation for the ``BaseExperiment.load_parameters()`` method.