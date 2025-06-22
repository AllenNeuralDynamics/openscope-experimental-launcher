Parameter Files
===============

Parameter files are JSON configuration files that define experiment-specific settings. They specify script paths, execution parameters, and output locations for individual experiments.

.. note::
   Parameter files contain **experiment-specific settings** only. Hardware settings 
   like rig_id belong in the rig configuration file. See :doc:`rig_config` for rig 
   configuration details and :doc:`configuration` for the complete system overview.

Core Parameters
---------------

These are the essential parameters that define your experiment:

**script_path** (string, required)
   Path to the experiment script, workflow, or program to execute:
   
   - ``.bonsai`` files for BonsaiLauncher
   - ``.py`` files for PythonLauncher  
   - ``.m`` files for MATLABLauncher
   - Any executable for BaseLauncher

**OutputFolder** (string, required)
   Directory where experiment data and outputs will be saved

**subject_id** (string, optional)
   Identifier for the experimental subject. If not provided, you'll be prompted at runtime.

**user_id** (string, optional)
   Identifier for the person running the experiment. If not provided, you'll be prompted at runtime.

Basic Example
~~~~~~~~~~~~~

.. code-block:: json
   :caption: Minimal parameter file

   {
       "script_path": "workflows/my_experiment.bonsai",
       "OutputFolder": "C:/experiment_data/session_001",
       "subject_id": "mouse_001",
       "user_id": "researcher"
   }

Optional Parameters
-------------------

**script_parameters** (object, optional)
   Interface-specific parameters passed to the script/workflow:
   
   - **Bonsai**: Passed as ``-p name=value`` command-line arguments
   - **MATLAB**: Available in the workspace during script execution
   - **Python**: Passed as command-line arguments or environment variables

**script_arguments** (array, optional)
   Additional command-line arguments passed directly to the script/program

Git Repository Parameters
--------------------------

For experiments stored in Git repositories:

**repository_url** (string, optional)
   Git repository URL containing the experiment code/workflows

**repository_commit_hash** (string, optional, default: "main")
   Specific commit, branch, or tag to checkout

**local_repository_path** (string, optional)
   Local directory where the repository should be cloned/stored

Runtime Data Collection
------------------------

The launcher can collect mouse weight and experiment information interactively:

.. code-block:: json
   :caption: Enable mouse weight collection

   {
       "script_path": "experiment.bonsai",
       "OutputFolder": "C:/experiment_data",
       "collect_mouse_runtime_data": true,
       "protocol_id": ["protocol_001"],
       "mouse_platform_name": "behavior_platform",
       "active_mouse_platform": true
   }

**collect_mouse_runtime_data** (boolean, optional)
   When true, prompts for animal weight before and after the experiment

**protocol_id** (array, optional)
   Protocol identifiers (user will be prompted to confirm at runtime)

**mouse_platform_name** (string, optional)
   Platform identifier (user will be prompted to confirm at runtime)

**active_mouse_platform** (boolean, optional)
   Platform status (user will be prompted to confirm at runtime)

**Runtime Prompts:**
   - Animal weight prior to experiment (at start)
   - Protocol and platform confirmation (simplified: press Enter to keep, or type new value)
   - Animal weight post experiment (at end)
   - Final experiment notes (optional)

Additional Parameter Examples
-----------------------------

Python Launcher Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: json
   :caption: Python launcher parameters

   {
       "repository_url": "https://github.com/user/python-experiment.git",
       "script_path": "experiments/visual_task.py",
       "repository_commit_hash": "main",
       "local_repository_path": "C:/repositories",
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
       "repository_url": "https://github.com/user/matlab-experiment.git",
       "script_path": "experiments/analysis_script.m",
       "repository_commit_hash": "main",
       "local_repository_path": "C:/repositories",
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

Additional Parameters
--------------------

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

For implementation details, see the ``initialize_launcher()`` method in the ``BaseLauncher`` class.

Session Files and Output
-------------------------

Every experiment automatically generates a comprehensive ``session.json`` file in the output directory using the AIND data schema format.

Session File Contents
~~~~~~~~~~~~~~~~~~~~~

The generated ``session.json`` includes:

- **Session Information**: Start/end times, session UUID, subject and user IDs
- **Data Streams**: Information about data collection streams and software  
- **Platform Details**: Rig identification, mouse platform configuration
- **Animal Data**: Pre/post experiment weights (when collected)
- **Software Information**: Details about the launcher and specific script/workflow executed
- **Experiment Parameters**: Complete parameter sets used during the experiment

Example Session File Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: json

   {
     "describedBy": "https://raw.githubusercontent.com/AllenNeuralDynamics/aind-data-schema/main/src/aind_data_schema/core/session.py",
     "schema_version": "1.4.0", 
     "experimenter_full_name": ["researcher_name"],
     "session_start_time": "2025-06-21T10:30:00.000000-07:00",
     "session_end_time": "2025-06-21T10:45:30.000000-07:00",
     "session_type": "OpenScope experiment",
     "rig_id": "your_rig_id",
     "subject_id": "test_mouse_001",
     "data_streams": [
       {
         "stream_start_time": "2025-06-21T10:30:00.000000-07:00",
         "stream_end_time": "2025-06-21T10:45:30.000000-07:00",
         "daq_names": ["Launcher"],
         "stream_modalities": [{"abbreviation": "BEH", "name": "Behavior"}]
       }
     ],
     "notes": "Experiment completed successfully with runtime data collection"
   }

Extending Session Metadata
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Custom launchers can add specific data streams by overriding the ``get_data_streams`` method:

.. code-block:: python

   class MyCustomLauncher(BonsaiLauncher):
       def get_data_streams(self, start_time, end_time):
           """Add custom data streams for this rig."""
           streams = super().get_data_streams(start_time, end_time)
           
           # Add custom stream for this rig
           streams.append({
               "stream_start_time": start_time,
               "stream_end_time": end_time, 
               "daq_names": ["MyCustomDAQ"],
               "stream_modalities": [{"abbreviation": "EPHYS", "name": "Electrophysiology"}]
           })
           
           return streams