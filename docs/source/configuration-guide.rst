OpenScope Configuration System Guide
===================================

The OpenScope experimental launcher uses a three-tier configuration system designed to separate rig-specific settings from experiment-specific parameters.

Configuration Types
------------------

1. Rig Configuration (TOML file)
   Purpose: Hardware and setup-specific settings that remain constant for a physical rig.

   Default Location:
   - Windows: ``C:/RigConfig/rig_config.toml``
   - Linux: ``/opt/rigconfig/rig_config.toml``

   Contains:
   - ``rig_id``: Unique identifier for this rig (defaults to hostname)
   - ``data_root_directory``: Base path for experiment data storage
   - Hardware-specific settings (camera configs, sync settings, etc.)

   Example::

     [rig]
     rig_id = "rig01"
     data_root_directory = "D:/OpenScopeData"

2. Parameter File (JSON)
   Purpose: Experiment-specific parameters, including subject, user, and session details.

   Example::

     {
       "subject_id": "mouse123",
       "user_id": "experimenter1",
       "output_root_folder": "D:/OpenScopeData"
     }

3. Command-line Overrides
   Purpose: Optional overrides for any parameter at runtime.

Notes
-----
- Rig configuration provides defaults for all experiments on a given rig.
- Parameter files are required for each experiment session.
- Command-line overrides are optional and take precedence over both.
