Rig Configuration
=================

The rig configuration file contains hardware and setup-specific settings that remain constant for a physical rig. This file is automatically created on first run and stores settings that should not change between experiments.

Purpose
-------

Rig configuration handles:

- **Hardware identification**: Unique rig identifier
- **Data storage paths**: Base directory for experiment data  
- **Hardware settings**: Camera configs, sync settings, etc.
- **Setup constants**: Values that remain the same across all experiments on this rig

File Location
-------------

The rig configuration file is stored at:

* ``C:/RigConfig/rig_config.toml``

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
   # Experiment parameters belong in JSON parameter files.   rig_id = "rig-001-behavior"
   output_root_folder = "C:/experiment_data"

Default Settings
----------------

When first created, the rig config contains:

**rig_id**
   Defaults to the computer's hostname. This uniquely identifies your rig.

**output_root_folder** 
   Default base directory for experiments. When experiments don't specify a custom output_root_folder,
   this directory will be used as the base for creating timestamped SessionFolders.
   
   Defaults to ``C:/experiment_data``.
   .. note::
      **Folder System**: The launcher uses a two-tier folder system:
      
      - **output_root_folder**: Base directory (from rig config or parameter override)
      - **output_session_folder**: output_root_folder + timestamped session name (automatically created)
      
      Your experiment processes receive the full output_session_folder path.

Adding Custom Settings
----------------------

You can add rig-specific hardware settings:

.. code-block:: toml   # Basic required settings
   rig_id = "ophys-rig-003"
   output_root_folder = "D:/experiment_data"

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

✅ **Do put in rig config:**
   - ``rig_id`` - hardware identifier
   - ``output_root_folder`` - base data path
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
   print(f"Data directory: {config['output_root_folder']}")


Related Documentation
---------------------

- :doc:`configuration` - Overview of the complete configuration system
- :doc:`parameter_files` - Experiment-specific parameter files
- :doc:`quickstart` - Getting started with your first experiment
