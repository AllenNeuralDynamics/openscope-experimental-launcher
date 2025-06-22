"""
MATLAB interface for OpenScope experimental launchers.

This module provides stateless functions for managing MATLAB process
interactions and script execution.
"""

import os
import logging
import subprocess
from typing import Dict, List, Optional, Any


def setup_matlab_environment(params: Dict[str, Any]) -> bool:
    """
    Set up MATLAB environment.
    
    Args:
        params: Parameter dictionary containing MATLAB configuration
        
    Returns:
        True if setup successful, False otherwise
    """
    # Check if MATLAB is available
    matlab_exe_path = params.get('matlab_exe_path', 'matlab')
    
    if not check_installation(matlab_exe_path):
        logging.error("MATLAB not found or not accessible")
        return False
    
    logging.info("MATLAB environment ready")
    return True


def check_installation(matlab_exe_path: str = 'matlab') -> bool:
    """
    Check if MATLAB is installed and accessible.
    
    Args:
        matlab_exe_path: Path to MATLAB executable (default: 'matlab')
        
    Returns:
        True if MATLAB is found, False otherwise
    """
    try:
        # Try to run MATLAB with version flag
        result = subprocess.run(
            [matlab_exe_path, '-batch', 'version; exit'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            logging.info("MATLAB installation verified")
            return True
        else:
            logging.warning(f"MATLAB check failed with return code: {result.returncode}")
            return False
            
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        logging.warning(f"MATLAB not found or not accessible: {e}")
        return False


def construct_matlab_arguments(params: Dict[str, Any]) -> List[str]:
    """
    Construct command-line arguments for MATLAB script execution.
    
    Args:
        params: Parameter dictionary
        
    Returns:
        List of command-line arguments
    """
    args = []
    
    # Use batch mode for non-interactive execution
    args.append('-batch')
      # Add custom MATLAB arguments if specified
    custom_args = params.get('script_arguments', [])
    if custom_args:
        args.extend(custom_args)
    
    return args


def start_matlab_script(script_path: str, matlab_exe_path: str = 'matlab', 
                       arguments: List[str] = None, output_folder: str = None) -> subprocess.Popen:
    """
    Start a MATLAB script as a subprocess.
    
    Args:
        script_path: Path to the MATLAB script file
        matlab_exe_path: Path to MATLAB executable
        arguments: Additional command-line arguments
        output_folder: Directory for output files
        
    Returns:
        Subprocess.Popen object for the running MATLAB process
    """
    if not os.path.exists(script_path):
        raise FileNotFoundError(f"MATLAB script not found: {script_path}")
    
    # Build command arguments
    cmd_args = [matlab_exe_path]
    
    if arguments:
        cmd_args.extend(arguments)
    
    # Add the script execution command
    script_dir = os.path.dirname(script_path)
    script_name = os.path.splitext(os.path.basename(script_path))[0]
      # Change to script directory and run the script
    matlab_command = f"cd('{script_dir}'); {script_name}; exit"
    
    if output_folder:
        # Add output folder as a MATLAB variable
        matlab_command = f"cd('{script_dir}'); output_folder='{output_folder}'; {script_name}; exit"
    
    cmd_args.extend(['-batch', matlab_command])
    
    logging.info(f"Starting MATLAB script: {' '.join(cmd_args)}")
    
    try:
        process = subprocess.Popen(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        logging.info(f"MATLAB script started with PID: {process.pid}")
        return process
        
    except Exception as e:
        logging.error(f"Failed to start MATLAB script: {e}")
        raise
