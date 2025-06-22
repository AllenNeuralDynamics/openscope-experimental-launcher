Configuration System
===================

The OpenScope Experimental Launcher uses a sophisticated three-tier configuration system designed to cleanly separate rig-specific settings from experiment-specific parameters.

Overview
--------

The configuration system provides:

- **Clean separation** of concerns between hardware setup and experiment design
- **Single source of truth** for rig identification and hardware settings  
- **Flexible parameter inheritance** with clear priority rules
- **Automatic setup** with sensible defaults for new rigs
- **Special case handling** for testing and development

Configuration Tiers
--------------------

1. Rig Configuration (TOML)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Hardware and setup-specific settings that remain constant for a physical rig.

**Location**: 
- Windows: ``C:/RigConfig/rig_config.toml``
- Linux: ``/opt/rigconfig/rig_config.toml``

**Contains**:
- ``rig_id``: Unique identifier for this rig (defaults to hostname)
- ``data_root_directory``: Base path for experiment data storage
- Hardware-specific settings (camera configs, sync settings, etc.)

**Example**:

.. code-block:: toml

   # OpenScope Rig Configuration
   # ==============================
   # This file contains settings specific to this physical rig setup.
   
   rig_id = "rig-001-behavior"
   data_root_directory = "C:/experiment_data"

**Auto-Creation**: The launcher automatically creates this file with sensible defaults on first run.

2. Experiment Parameters (JSON)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Experiment-specific settings that change per experiment or session.

**Contains**:
- ``subject_id``: Subject being tested
- ``user_id``: User running the experiment
- ``protocol_id``: Experimental protocol being run
- ``OutputFolder``: Session-specific output directory
- Stimulus parameters, session settings, etc.

**Example**:

.. code-block:: json

   {
       "subject_id": "mouse_001",
       "user_id": "researcher",
       "protocol_id": ["detection_of_change"],
       "OutputFolder": "C:/experiment_data/2024-01-15/mouse_001",
       "script_path": "workflows/stimulus_presentation.bonsai",
       "stimulus_params": {
           "contrast": 0.8,
           "spatial_frequency": 0.04
       }
   }

3. Runtime Information
~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Interactive collection of missing required values.

**Collected when**:
- Required values are missing from both rig config and experiment parameters
- User needs to confirm or override certain settings

**Examples**:
- Prompting for subject_id if not in JSON file
- Confirming protocol settings before experiment start
- Collecting animal weights at start/end of experiment

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
     - Interactive user input overrides everything
   * - 2 (Medium)  
     - JSON Parameters
     - Experiment-specific settings override rig defaults
   * - 3 (Lowest)
     - Rig Configuration
     - Hardware/setup defaults used as fallback

Parameter Placement Guidelines
------------------------------

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
     - Hardware identifier, constant per rig
   * - data_root_directory
     - ✅
     - ❌
     - ❌
     - Base data path, rig-specific
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
     - Experiment design parameter
   * - OutputFolder
     - ❌
     - ✅
     - ❌
     - Session-specific output location
   * - stimulus_params
     - ❌
     - ✅
     - ❌
     - Experiment-specific settings

Usage Patterns
---------------

Normal Operation
~~~~~~~~~~~~~~~~

**Recommended for production use:**

.. code-block:: python

   from openscope_experimental_launcher.launchers import BonsaiLauncher

   # Create launcher
   launcher = BonsaiLauncher()
   
   # Initialize with parameter file (uses default rig config)
   launcher.initialize_launcher(param_file="experiment.json")
   
   # Run experiment
   success = launcher.run("experiment.json")

**Why this is recommended:**
- Uses default rig config location (predictable, standard)
- Clean separation between rig setup and experiment parameters
- Automatic rig config creation on first run
- Consistent behavior across all rigs

Testing and Development  
~~~~~~~~~~~~~~~~~~~~~~~

**For testing or non-standard setups:**

.. code-block:: python

   # ONLY for special cases!
   launcher.initialize_launcher(
       param_file="test_params.json",
       rig_config_path="/path/to/test_rig_config.toml"
   )

**When to use custom rig_config_path:**
- Unit testing with mock rig configurations
- Development with multiple test setups
- Non-standard rig installations
- Debugging configuration issues

**Do NOT use for:**
- Normal experiment operation
- Production deployments
- Standard rig setups

Best Practices
--------------

Rig Configuration
~~~~~~~~~~~~~~~~~

1. **Keep it minimal** - Only hardware/setup constants
2. **Use descriptive rig_id** - e.g., "ophys-rig-001" not just "rig1"
3. **Document custom settings** - Add comments for non-standard configurations
4. **Version control templates** - Keep standard rig configs in git for new setups

Experiment Parameters
~~~~~~~~~~~~~~~~~~~~~

1. **Use descriptive file names** - e.g., "2024-01-15_mouse001_detection.json"
2. **Create parameter templates** - Reuse configurations for similar experiments  
3. **Include all experiment settings** - Don't rely on hardcoded defaults
4. **Validate before running** - Check required fields are present

Project Organization
~~~~~~~~~~~~~~~~~~~~

**Recommended file structure:**

.. code-block:: text

   C:/RigConfig/
   ├── rig_config.toml              # Rig-specific settings

   C:/experiments/
   ├── daily_experiments/
   │   ├── 2024-01-15_mouse001.json # Today's experiment parameters
   │   ├── 2024-01-15_mouse002.json 
   │   └── ...
   ├── protocol_templates/
   │   ├── detection_of_change.json # Reusable protocol templates
   │   ├── visual_behavior.json
   │   └── ...

API Reference
-------------

initialize_launcher()
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def initialize_launcher(self, param_file: Optional[str] = None, 
                          rig_config_path: Optional[str] = None):
       """
       Initialize the launcher by loading all required configuration and data.
       
       Args:
           param_file: Path to JSON file containing experiment-specific parameters.
                      If None, only rig config and runtime prompts will be used.
           rig_config_path: Optional override path to rig config file. 
                          **ONLY use this for special cases like testing.**
                          In normal operation, leave this as None.
       """

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**"rig_id not found" Error**
   - Check that rig config file exists at default location
   - Verify the rig config file contains a valid ``rig_id`` field
   - For testing, create a custom rig config with a test rig_id

**"Configuration key not found" Error**
   - Check if the key should be in rig config (hardware) or JSON parameters (experiment)
   - Verify the parameter file contains all required experiment-specific settings
   - Check if the value should be collected at runtime instead

**"No such file or directory" for rig config**
   - The launcher will automatically create a default rig config on first run
   - Check file permissions in the rig config directory
   - For custom locations, ensure the directory exists and is writable

Performance Considerations
~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Don't override rig_config_path unnecessarily** - optimized for default location
- **Use JSON parameter templates** - avoid recreating similar configurations
- **Cache parameter files** - reuse validated configurations when possible

Migration from Legacy Systems
-----------------------------

If upgrading from older launcher versions:

1. **Extract rig-specific settings** from old parameter files into rig config
2. **Remove rig_id from JSON files** - now handled by rig config
3. **Update initialization calls** - use ``initialize_launcher()`` instead of ``load_parameters()``
4. **Review parameter placement** - ensure settings are in the correct tier

For detailed migration assistance, see the project documentation or contact the development team.
