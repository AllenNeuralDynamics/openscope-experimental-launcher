"""
Configuration loader for OpenScope experimental launchers.

DEPRECATED: This module uses CamStim-compatible configuration files.
It will be replaced by the new rig_config.py system.

New code should use: from ..utils import rig_config
"""

import os
import logging
import warnings
from typing import Dict, Any
try:
    import configparser
except ImportError:
    import ConfigParser as configparser
import io
import ast

# Issue deprecation warning
warnings.warn(
    "config_loader.py is deprecated and will be removed in a future version. "
    "Use rig_config.py for new code.",
    DeprecationWarning,
    stacklevel=2
)

# Default CamStim configuration
DEFAULTCONFIG = """
[Behavior]
nidevice = Dev1
volume_limit = 1.5
sync_sqr = True
sync_sqr_loc = (-300,-300)
sync_pulse = True
pulseOnRisingEdge = True
pulsedigitalport = 1
pulsedigitalline = 0
sync_nidevice = Dev1
display_time = True
mouse_id = test_mouse
user_id = test_user

[Encoder]
nidevice = Dev1
encodervinchannel = 0
encodervsigchannel = 1

[Reward]
reward_volume = 0.007
nidevice = Dev1
reward_lines = [(0,0)]
invert_logic = False

[Licksensing]
nidevice = Dev1
lick_lines = [(0,1)]

[Sync]
sync_sqr = True
sync_sqr_loc = (-300,-300)

[Stim]
showmouse = False
miniwindow = False
fps = 60.000
monitor_brightness = 30
monitor_contrast = 50

[LIMS]
lims_upload = False
lims_dummy = True

[SweepStim]
backupdir = None
mouseid = 'test'
userid = 'user'
bgcolor = (0,0,0)
controlstream = True
trigger = None
triggerdiport = 0
triggerdiline = 0
trigger_delay_sec = 0.0
savesweeptable = True
eyetracker = False

[Display]
monitor = 'testMonitor'
screen = 1
projectorType = 'Projector.Normal'
warp = 'Warp.Disabled'
warpfile = None
flipHorizontal = False
flipVertical = False
eyepoint = (0.5,0.5)

[Datastream]
data_export = False
data_export_port = 5000
data_export_rep_port = 5001
"""


def _get_default_config_dir() -> str:
    """Get the default CamStim configuration directory for Windows."""
    return "C:/ProgramData/AIBS_MPE/camstim/"


def _load_config_section(section: str, config: configparser.RawConfigParser) -> Dict[str, Any]:
    """
    Load a section from the config file.
    
    Args:
        section: Section name
        config: ConfigParser object
        
    Returns:
        Dictionary containing section configuration
    """
    section_config = {}
    
    try:
        if config.has_section(section):
            for key, value in config.items(section):
                try:
                    # Use ast.literal_eval for safe evaluation (SECURITY FIX)
                    section_config[key] = ast.literal_eval(value)
                except (ValueError, SyntaxError):
                    # If literal_eval fails, keep as string
                    section_config[key] = value
        
        logging.debug(f"Loaded config section: {section}")
        
    except Exception as e:
        logging.warning(f"Failed to load config section {section}: {e}")
    
    return section_config


def load_config(params: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Load configuration from CamStim config files.
    
    Args:
        params: Experiment parameters that may contain config path overrides
        
    Returns:
        Dictionary containing all configuration sections
    """
    default_config_dir = _get_default_config_dir()
    default_config_path = os.path.join(default_config_dir, "config", "stim.cfg")
    config_path = params.get("config_path", default_config_path)
    
    # Ensure config directory exists
    config_dir = os.path.dirname(config_path)
    if not os.path.isdir(config_dir):
        os.makedirs(config_dir)
    
    # Create default config file if it doesn't exist
    if not os.path.isfile(config_path):
        logging.info(f"Config file not found, creating default at {config_path}")
        with open(config_path, 'w') as f:
            f.write(DEFAULTCONFIG)
    
    # Load configuration
    logging.info(f"Loading configuration from {config_path}")
    
    try:
        config = configparser.RawConfigParser()
        config.read_file(io.StringIO(DEFAULTCONFIG))
        config.read(config_path)
        
        # Load all sections into dictionary
        result = {}
        for section_name in ['Behavior', 'Encoder', 'Reward', 'Licksensing', 
                           'Sync', 'Stim', 'LIMS', 'SweepStim', 'Display', 'Datastream']:
            result[section_name] = _load_config_section(section_name, config)
        
        return result
        
    except Exception as e:
        logging.warning(f"Error reading config file: {e}")
        return {}
