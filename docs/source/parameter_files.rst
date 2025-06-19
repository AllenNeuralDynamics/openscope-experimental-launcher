Parameter Files
===============

Parameter files are JSON configuration files that define how experiments are run. They specify script paths, execution parameters, and output locations. The parameter structure is now unified across all launcher types, using ``script_path`` as the primary parameter for specifying the experiment to run.

Basic Parameter Structure
-------------------------

.. code-block:: json
   :caption: Basic parameter file structure

   {
       "script_path": "path/to/script.py",
       "OutputFolder": "C:/experiment_data"
   }

Universal Parameters
--------------------

These parameters work across all launcher types:

**script_path** (string)
   Path to the experiment script, workflow, or program to execute. This can be:
   
   - ``.bonsai`` files for BonsaiLauncher
   - ``.py`` files for PythonLauncher  
   - ``.m`` files for MATLABLauncher
   - Any executable for BaseLauncher

**OutputFolder** (string)
   Directory where experiment data and outputs will be saved

Launcher-Specific Parameter Files
---------------------------------

Bonsai Launcher Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~

For Bonsai workflows, additional Git repository parameters are supported:

.. code-block:: json
   :caption: Bonsai launcher parameters

   {
       "repository_url": "https://github.com/user/repo.git",
       "script_path": "workflows/visual_stimulus.bonsai",
       "repository_commit_hash": "main",
       "OutputFolder": "C:/experiment_data"
   }

**repository_url** (string, optional)
   Git repository URL containing the Bonsai workflow

**repository_commit_hash** (string, optional, default: "main")
   Specific commit, branch, or tag to checkout

Runtime Information Collection
-----------------------------

The following information is collected interactively when you run an experiment:

**subject_id** (string)
   Unique identifier for the experimental subject (collected at runtime)

**user_id** (string)  
   Identifier for the person running the experiment (collected at runtime)

**rig_id** (string, optional)
   Identifier for the experimental rig (collected at runtime if needed)

Additional Parameter Examples
-----------------------------

Python Launcher Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: json
   :caption: Python launcher parameters

   {
       "script_path": "experiments/visual_task.py",
       "OutputFolder": "C:/experiment_data",
       "python_parameters": {
           "num_trials": 100,
           "stimulus_duration": 2.0,
           "subject_id": "mouse_001"
       }
   }

MATLAB Launcher Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: json
   :caption: MATLAB launcher parameters

   {
       "script_path": "experiments/analysis_script.m",
       "OutputFolder": "C:/experiment_data",
       "matlab_parameters": {
           "data_path": "C:/raw_data",
           "analysis_type": "spectral",
           "gpu_enabled": true
       }
   }

Minimalist Launcher Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: json
   :caption: Minimalist launcher parameters (no Git dependencies)

   {
       "script_path": "C:/local/workflows/simple_task.bonsai",
       "OutputFolder": "C:/experiment_data"
   }

Optional Parameters
-------------------

These parameters can be added to any parameter file:

**local_repository_path** (string, default: "C:/BonsaiTemp")
   Local directory for cloning Git repositories (BonsaiLauncher only)

**session_type** (string, default: "experiment")
   Type of experimental session for metadata

**additional_parameters** (object)
   Interface-specific parameters passed to the script or workflow

Script-Specific Parameters
---------------------------

Pass parameters directly to your scripts using interface-specific sections:

Bonsai Parameters
~~~~~~~~~~~~~~~~~

.. code-block:: json

   {
       "script_path": "workflow.bonsai",
       "OutputFolder": "C:/data",
       "bonsai_parameters": {
           "NumTrials": 100,
           "StimulusDuration": 5.0,
           "InterTrialInterval": 2.0,
           "RewardSize": 0.01
       }
   }

Python Parameters
~~~~~~~~~~~~~~~~~

.. code-block:: json

   {
       "script_path": "experiment.py",
       "OutputFolder": "C:/data",
       "python_parameters": {
           "num_trials": 100,
           "stimulus_type": "gratings",
           "save_raw_data": true
       }
   }

MATLAB Parameters
~~~~~~~~~~~~~~~~~

.. code-block:: json

   {
       "script_path": "analysis.m",
       "OutputFolder": "C:/data",
       "matlab_parameters": {
           "data_file": "raw_data.mat",
           "analysis_type": "spectral",
           "plot_results": true
       }
   }

.. note::
   Parameters are passed to scripts in a format appropriate for each interface. Bonsai receives them as workflow properties, Python as command-line arguments or environment variables, and MATLAB as function parameters.

Legacy Parameter Support
------------------------

For backward compatibility, the following legacy parameter names are still supported but deprecated:

**bonsai_path** → **script_path**
   Old parameter name for Bonsai workflow paths

**workflow_path** → **script_path**
   Alternative legacy parameter name

.. warning::
   Legacy parameter names will be removed in future versions. Please update your parameter files to use ``script_path``.

Configuration File Integration
------------------------------

The launcher can load settings from CamStim-style configuration files:

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