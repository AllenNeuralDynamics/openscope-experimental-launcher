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

See :doc:`rig_config` for complete details on rig configuration setup and options.

2. Experiment Parameters (JSON)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Experiment-specific settings that change per experiment.

See :doc:`parameter_files` for complete details on parameter file structure and options.

3. Runtime Information
~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Interactive collection of missing required values.

The launcher will prompt for any required values not found in the rig config or parameter files.

Configuration Priority
-----------------------

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
   * - data_root_directory
     - ✅
     - ❌
     - ❌
     - Base data path
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