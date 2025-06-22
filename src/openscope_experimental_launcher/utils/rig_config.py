"""Simple rig configuration system for OpenScope experimental launcher.

This module handles rig-specific configuration that stays constant across experiments.
Rig configuration provides hardware and setup specific settings like:
- rig_id: Unique identifier for this physical rig setup  
- output_root_folder: Base path for experiment data storage
- Hardware-specific settings (camera configs, sync settings, etc.)

IMPORTANT: Experiment-specific parameters should be in JSON parameter files, NOT in rig config.
JSON parameter files should contain:
- subject_id: Subject being tested
- user_id: User running the experiment  
- protocol_id: Experimental protocol being run
- stimulus parameters, session settings, etc.

Configuration Loading Priority:
1. Runtime prompts (highest priority - can override anything)
2. JSON parameter files (experiment-specific settings)
3. Rig config (hardware/setup defaults - lowest priority)
"""

import os
import logging
import socket
from pathlib import Path
from typing import Dict, Any, Optional
import toml

logger = logging.getLogger(__name__)

# Sentinel value to distinguish between "no default" and "default is None"
_MISSING = object()

# Default configuration file path
DEFAULT_CONFIG_PATH = Path("C:/RigConfig/rig_config.toml") if os.name == 'nt' else Path("/opt/rigconfig/rig_config.toml")

# Default configuration values - single source of truth
DEFAULT_CONFIG = {
    'rig_id': socket.gethostname(),  # Use hostname to identify this rig
    'output_root_folder': 'C:/experiment_data',
}


def get_config_path(config_path: Optional[str] = None) -> Path:
    """Get the rig configuration file path."""
    return Path(config_path) if config_path else DEFAULT_CONFIG_PATH


def create_default_config(config_path: Path) -> None:
    """Create a default rig configuration file."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write("# OpenScope Rig Configuration\n")
        f.write("# ==============================\n")
        f.write("# This file contains settings specific to this physical rig setup.\n")
        f.write("# These settings should remain constant across different experiments.\n")
        f.write("#\n")
        f.write("# DO NOT put experiment-specific parameters here!\n")
        f.write("# Experiment parameters belong in JSON parameter files:\n") 
        f.write("# - subject_id, user_id, protocol_id\n")
        f.write("# - stimulus parameters, session settings, etc.\n")
        f.write("#\n")
        f.write("# rig_id: Unique identifier for this rig (defaults to hostname)\n")
        f.write("# output_root_folder: Base path for storing experiment data\n")
        f.write("#\n\n")
        toml.dump(DEFAULT_CONFIG, f)
    
    logger.info(f"Created default rig configuration at {config_path}")


def load_config(config_path: Optional[str] = None, create_if_missing: bool = True) -> Dict[str, Any]:
    """Load rig configuration from TOML file."""
    config_file_path = get_config_path(config_path)
    
    if not config_file_path.exists():
        if create_if_missing:
            logger.info(f"Rig config not found at {config_file_path}, creating default")
            create_default_config(config_file_path)
        else:
            logger.warning(f"Rig config not found at {config_file_path}, using defaults")
            return DEFAULT_CONFIG.copy()
    
    try:
        logger.info(f"Loading rig configuration from {config_file_path}")
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config = toml.load(f)
        
        # Merge with defaults to ensure all required fields are present
        merged_config = DEFAULT_CONFIG.copy()
        merged_config.update(config)
        
        # Validate required fields
        if 'rig_id' not in merged_config or not merged_config['rig_id'].strip():
            raise ValueError("Required field 'rig_id' missing or empty in rig config")
        
        logger.info(f"Loaded rig configuration for rig: {merged_config.get('rig_id', 'unknown')}")
        return merged_config
        
    except Exception as e:
        logger.error(f"Failed to load rig configuration: {e}")
        logger.info("Using default configuration as fallback")
        return DEFAULT_CONFIG.copy()


def get_config(key: str, config_path: Optional[str] = None, default: Any = _MISSING) -> Any:
    """Get a specific configuration value.
    
    Args:
        key: Configuration key to retrieve
        config_path: Path to rig config file. If None, uses default location.
        default: Default value to return if key not found. If not provided, raises KeyError.
        
    Returns:
        Configuration value or default
        
    Raises:
        KeyError: If key is not found and no default is provided
    """
    config = load_config(config_path, create_if_missing=False)
    
    if key in config:
        return config[key]
    elif default is not _MISSING:
        return default
    else:
        available_keys = list(config.keys())
        raise KeyError(f"Configuration key '{key}' not found. Available keys: {available_keys}")


def get_rig_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Get the complete rig configuration.
    
    This is the main function that should be called by the launcher.
    """
    return load_config(config_path, create_if_missing=True)