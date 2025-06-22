Rig Configuration
=================

The rig configuration file contains hardware and setup-specific settings that remain constant for a physical rig. This file is automatically created on first run and stores settings that should not change between experiments.

Purpose
-------

Rig configuration handles:

- **Hardware identification**: Unique rig identifier
- **Data storage paths**: Base directories for experiment data
- **Hardware settings**: Camera configs, sync settings, etc.
- **Setup constants**: Values that remain the same across all experiments on this rig

File Location
-------------

The rig configuration file is stored at:

- **Windows**: ``C:/RigConfig/rig_config.toml``
- **Linux**: ``/opt/rigconfig/rig_config.toml``

.. note::
   The launcher automatically creates this file with sensible defaults on first run.
   You can edit it manually or let the launcher manage it.

File Format
-----------

The rig config uses TOML format for easy reading and editing:

.. code-block:: toml

   # OpenScope Rig Configuration
   # ==============================
   # This file contains settings specific to this physical rig setup.
   # These settings should remain constant across different experiments.
   #
   # DO NOT put experiment-specific parameters here!
   # Experiment parameters belong in JSON parameter files.

   rig_id = "rig-001-behavior"
   data_root_directory = "C:/experiment_data"

Default Settings
----------------

When first created, the rig config contains:

**rig_id**
   Defaults to the computer's hostname. This uniquely identifies your rig.

**data_root_directory**
   Base path for storing experiment data. Defaults to:
   
   - Windows: ``C:/experiment_data``
   - Linux: ``/home/experiment_data``

Adding Custom Settings
----------------------

You can add rig-specific hardware settings:

.. code-block:: toml

   # Basic required settings
   rig_id = "ophys-rig-003"
   data_root_directory = "D:/experiment_data"

   # Example: Camera settings
   [camera]
   exposure_time = 0.033
   gain = 1.0
   resolution = [1024, 1024]

   # Example: Sync settings
   [sync]
   sample_rate = 30000
   input_channels = ["barcode", "vsync", "photodiode"]

.. important::
   Only add settings that are **constant for this rig**. Settings that change 
   per experiment belong in parameter files, not rig config.

What NOT to Put Here
--------------------

**Experiment-specific settings** should go in parameter files instead:

❌ **Don't put in rig config:**
   - ``subject_id`` - changes per experiment
   - ``user_id`` - changes per session
   - ``protocol_id`` - experiment design parameter
   - ``script_path`` - experiment workflow
   - ``OutputFolder`` - session-specific output location

✅ **Do put in rig config:**
   - ``rig_id`` - hardware identifier
   - ``data_root_directory`` - base data path
   - Camera settings, sync settings, hardware configs

Editing the Rig Config
-----------------------

Manual Editing
~~~~~~~~~~~~~~

You can edit the rig config file directly:

1. Open ``C:/RigConfig/rig_config.toml`` in a text editor
2. Make your changes
3. Save the file
4. Restart your launcher application

The file will be validated when the launcher starts.

Programmatic Access
~~~~~~~~~~~~~~~~~~~

You can also access rig config programmatically:

.. code-block:: python

   from openscope_experimental_launcher.utils.rig_config import get_rig_config

   # Load current rig configuration
   config = get_rig_config()
   print(f"Current rig: {config['rig_id']}")
   print(f"Data directory: {config['data_root_directory']}")

Testing with Custom Configs
----------------------------

For testing, you can use a custom rig config file:

.. code-block:: python

   # Only for testing!
   launcher.initialize_launcher(
       param_file="experiment.json",
       rig_config_path="/path/to/test_rig_config.toml"
   )

.. warning::
   Custom rig config paths should only be used for testing or special setups.
   Normal operation should always use the default location.

Validation
----------

The launcher validates rig config on startup:

**Required Fields:**
   - ``rig_id`` must be present and non-empty

**Automatic Fixes:**
   - Missing fields are filled with defaults
   - Invalid values are corrected where possible

**Error Handling:**
   - If the file is corrupted, a new default file is created
   - Validation errors are logged with helpful messages

Best Practices
--------------

1. **Use descriptive rig_id**: e.g., "ophys-rig-001" not just "rig1"
2. **Keep it minimal**: Only add settings that are truly rig-specific
3. **Document custom settings**: Add comments explaining non-standard configurations
4. **Version control**: Keep template rig configs in git for new rig setups
5. **Backup before major changes**: Save a copy before making significant edits

Multiple Rigs
-------------

If you manage multiple rigs:

**Option 1: Default locations per machine**
   Each rig computer has its own rig config at the default location.

**Option 2: Custom locations (advanced)**
   Use custom rig config paths for each rig, but this requires updating launcher scripts.

**Recommended**: Use Option 1 for simplicity and consistency.

Related Documentation
---------------------

- :doc:`configuration` - Overview of the complete configuration system
- :doc:`parameter_files` - Experiment-specific parameter files
- :doc:`quickstart` - Getting started with your first experiment
