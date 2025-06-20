"""
Python interface for OpenScope experimental launchers.

This module provides stateless functions for managing Python process
interactions and script execution.
"""

import os
import sys
import logging
import subprocess
from typing import Dict, List, Optional, Any


def setup_python_environment(params: Dict[str, Any]) -> bool:
    """
    Set up Python environment including virtual environment if specified.
    
    Args:
        params: Parameter dictionary containing Python configuration
        
    Returns:
        True if setup successful, False otherwise
    """
    # Check if Python is available
    python_exe_path = params.get('python_exe_path', sys.executable)
    
    if not check_installation(python_exe_path):
        logging.error("Python not found or not accessible")
        return False
    
    # Check for virtual environment
    venv_path = params.get('python_venv_path')
    if venv_path:
        if not activate_virtual_environment(venv_path):
            logging.warning("Failed to activate virtual environment, using system Python")
    
    logging.info("Python environment ready")
    return True


def check_installation(python_exe_path: str = None) -> bool:
    """
    Check if Python is installed and accessible.
    
    Args:
        python_exe_path: Path to Python executable (default: sys.executable)
        
    Returns:
        True if Python is found, False otherwise
    """
    if python_exe_path is None:
        python_exe_path = sys.executable
    
    try:
        # Try to run Python with version flag
        result = subprocess.run(
            [python_exe_path, '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logging.info(f"Python installation verified: {result.stdout.strip()}")
            return True
        else:
            logging.warning(f"Python check failed with return code: {result.returncode}")
            return False
            
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        logging.warning(f"Python not found or not accessible: {e}")
        return False


def activate_virtual_environment(venv_path: str) -> bool:
    """
    Activate a Python virtual environment.
    
    Args:
        venv_path: Path to the virtual environment
        
    Returns:
        True if activation successful, False otherwise
    """
    if not os.path.exists(venv_path):
        logging.error(f"Virtual environment not found: {venv_path}")
        return False
    
    # Check for activation script
    activate_script = os.path.join(venv_path, 'Scripts', 'activate.bat')  # Windows
    if not os.path.exists(activate_script):
        activate_script = os.path.join(venv_path, 'bin', 'activate')  # Unix/Linux
    
    if not os.path.exists(activate_script):
        logging.error(f"Virtual environment activation script not found: {activate_script}")
        return False
    
    logging.info(f"Virtual environment found: {venv_path}")
    # Note: For subprocess execution, we'll use the venv's Python executable directly
    return True


def construct_python_arguments(params: Dict[str, Any]) -> List[str]:
    """
    Construct command-line arguments for Python script execution.
    
    Args:
        params: Parameter dictionary
        
    Returns:
        List of command-line arguments
    """
    args = []
    
    # Add custom Python arguments if specified
    custom_args = params.get('script_arguments', [])
    if custom_args:
        args.extend(custom_args)
    
    # Add script arguments from parameters
    script_args = params.get('script_arguments', [])
    if script_args:
        args.extend(script_args)
    
    return args


def start_python_script(script_path: str, python_exe_path: str = None, 
                       arguments: List[str] = None, output_path: str = None,
                       venv_path: str = None) -> subprocess.Popen:
    """
    Start a Python script as a subprocess.
    
    Args:
        script_path: Path to the Python script file
        python_exe_path: Path to Python executable
        arguments: Additional command-line arguments
        output_path: Directory for output files
        venv_path: Path to virtual environment (if applicable)
        
    Returns:
        Subprocess.Popen object for the running Python process
    """
    if not os.path.exists(script_path):
        raise FileNotFoundError(f"Python script not found: {script_path}")
    
    # Determine Python executable
    if venv_path and os.path.exists(venv_path):
        # Use virtual environment's Python
        venv_python = os.path.join(venv_path, 'Scripts', 'python.exe')  # Windows
        if not os.path.exists(venv_python):
            venv_python = os.path.join(venv_path, 'bin', 'python')  # Unix/Linux
        
        if os.path.exists(venv_python):
            python_exe_path = venv_python
            logging.info(f"Using virtual environment Python: {python_exe_path}")
    
    if python_exe_path is None:
        python_exe_path = sys.executable
    
    # Build command arguments
    cmd_args = [python_exe_path, script_path]
    
    if arguments:
        cmd_args.extend(arguments)
    
    # Set environment variables
    env = os.environ.copy()
    if output_path:
        env['OUTPUT_PATH'] = output_path
        logging.info(f"Output path set as environment variable: {output_path}")
    
    logging.info(f"Starting Python script: {' '.join(cmd_args)}")
    
    try:
        process = subprocess.Popen(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1,
            env=env
        )
        
        logging.info(f"Python script started with PID: {process.pid}")
        return process
        
    except Exception as e:
        logging.error(f"Failed to start Python script: {e}")
        raise
