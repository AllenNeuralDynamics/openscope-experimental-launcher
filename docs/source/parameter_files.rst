Parameter Files
===============

Parameter files are JSON configuration files that define how experiments are run. They specify script paths, execution parameters, and output locations. The parameter structure is now unified across all launcher types, using ``script_path`` as the primary parameter for specifying the experiment to run, and ``script_parameters`` for interface-specific configuration.

Basic Parameter Structure
-------------------------

.. code-block:: json
   :caption: Basic parameter file structure

   {
       "script_path": "path/to/script.py",
       "OutputFolder": "C:/experiment_data",
       "script_parameters": {
           "param1": "value1",
           "param2": 42
       }
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

**script_parameters** (object, optional)
   Interface-specific parameters passed to the script/workflow. The format and usage depends on the launcher type:
   
   - For Bonsai: Passed as ``-p name=value`` command-line arguments
   - For MATLAB: Available in the workspace during script execution
   - For Python: Passed as command-line arguments or environment variables

**script_arguments** (array, optional)
   Additional command-line arguments passed directly to the script/program

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
       "script_parameters": {
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
       "script_parameters": {
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
       "script_parameters": {
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
       "script_parameters": {
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
       "script_parameters": {
           "data_file": "raw_data.mat",
           "analysis_type": "spectral",
           "plot_results": true
       }
   }

.. note::
   Parameters are passed to scripts in a format appropriate for each interface. Bonsai receives them as workflow properties (``-p name=value``), Python as command-line arguments or environment variables, and MATLAB as function parameters.


Parameter Schema Reference
--------------------------

For a complete schema definition, see the :doc:`api/base` documentation for the ``BaseExperiment.load_parameters()`` method.