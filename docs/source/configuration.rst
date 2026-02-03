Configuration System
===================

The OpenScope Experimental Launcher uses a three-tier configuration system that cleanly separates rig-specific settings from experiment-specific parameters.

Overview
--------

The system provides:

- **Clean separation** between hardware setup and experiment design
- **Single source of truth** for rig identification
- **Automatic setup** with sensible defaults
- **Flexible parameter inheritance** with clear priority rules

Configuration Tiers
--------------------

1. Rig Configuration (TOML)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Hardware and setup-specific settings that remain constant for a physical rig.

Default Location:

* ``C:/RigConfig/rig_config.toml``

Contains:

- ``rig_id``: Unique identifier for this rig (defaults to hostname)
- ``data_root_directory``: Base path for experiment data storage
- Hardware-specific settings (camera configs, sync settings, etc.)

See :doc:`rig_config` for complete details on rig configuration setup and options.

Example::

  [rig]
  rig_id = "rig01"
  data_root_directory = "D:/OpenScopeData"

2. Experiment Parameters (JSON)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Experiment-specific settings that change per experiment.

See :doc:`parameter_files` for complete details on parameter file structure and options.

Example::

  {
    "subject_id": "mouse123",
    "user_id": "experimenter1",
    "output_root_folder": "D:/OpenScopeData"
  }

3. Runtime Information
~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Interactive collection of missing required values.

The launcher will prompt for any required values not found in the rig config or parameter files.

Configuration Priority
-----------------------

The system merges configuration from all sources, with later sources overriding earlier ones:

1. **Base**: Rig configuration provides hardware defaults
2. **Override**: JSON parameter file values override rig config defaults  
3. **Final**: Runtime prompts override both rig config and JSON parameters

When the same parameter appears in multiple places:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Priority
     - Source
     - Description
   * - 1 (Highest)
     - Runtime Prompts
     - Interactive user input
   * - 2 (Medium)  
     - JSON Parameters
     - Experiment-specific settings
   * - 3 (Lowest)
     - Rig Configuration
     - Hardware defaults

What Goes Where
---------------

.. list-table::
   :header-rows: 1
   :widths: 25 15 15 15 35

   * - Parameter Type
     - Rig Config
     - JSON File
     - Runtime
     - Notes

   * - rig_id
     - ✅
     - ❌
     - ❌
     - Hardware identifier
   * - output_root_folder
     - ✅
     - ✅
     - ❌
     - Base directory (JSON overrides rig config default)
   * - subject_id
     - ❌
     - ✅
     - ✅
     - Changes per experiment
   * - user_id
     - ❌
     - ✅
     - ✅
     - Changes per session
   * - protocol_id
     - ❌
     - ✅
     - ❌
     - Experiment design
   * - script_path
     - ❌
     - ✅
     - ❌
     - Experiment workflow

Folder Structure System
-----------------------

The launcher uses a clear two-tier folder structure:

**output_root_folder** (Base Directory)
   - **Source Priority**: Parameter file ``output_root_folder`` > Rig config ``output_root_folder`` > Current directory
   - **Purpose**: Base directory where all experiments for this rig are stored
   - **Example**: ``C:/experiment_data``

**output_session_folder** (Specific Session)
   - **Creation**: Automatically created as output_root_folder + timestamped session name
   - **Format**: ``{subject_id}_{YYYY-MM-DD_HH-MM-SS}`` (AIND compliant when available)
   - **Purpose**: Specific directory passed to experiment processes
   - **Example**: ``C:/experiment_data/mouse_001_2025-06-22_14-30-15``

**Process Integration**
   Your experiment scripts/workflows receive the full **output_session_folder** path, not the output_root_folder.