"""
Python launcher for OpenScope experiments.

This module provides a launcher for running Python scripts.
"""

import os
import subprocess
import logging
from .base_launcher import BaseLauncher
from ..interfaces import python_interface
from ..utils import git_manager


class PythonLauncher(BaseLauncher):
    """
    Launcher for Python-based OpenScope experiments.
    
    Extends BaseLauncher with Python-specific process creation and
    virtual environment support.
    """
    
    def _get_launcher_type_name(self) -> str:
        """Get the name of the launcher type for logging."""
        return "Python"
    
    def create_process(self) -> subprocess.Popen:
        """
        Create the Python subprocess.
        
        Returns:
            subprocess.Popen object for the running Python script
        """
        # Setup Python environment
        if not python_interface.setup_python_environment(self.params):
            raise RuntimeError("Failed to setup Python environment")
        
        # Get script path
        script_path = self._get_script_path()
        
        # Construct arguments
        script_args = python_interface.construct_python_arguments(self.params)
        
        # Start Python script
        python_exe_path = self.params.get('python_exe_path')
        venv_path = self.params.get('python_venv_path')
        
        process = python_interface.start_python_script(
            script_path=script_path,
            python_exe_path=python_exe_path,
            arguments=script_args,
            output_folder=self.output_session_folder,
            venv_path=venv_path
        )
        
        return process

    @classmethod
    def run_from_params(cls, param_file):
        """
        Run the experiment with the specified parameters (Python version).
        
        Args:
            param_file: Path to the JSON parameter file
            
        Returns:
            True if successful, False otherwise
        """
        # Set up basic logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        try:
            if param_file and not os.path.exists(param_file):
                logging.error(f"Parameter file not found: {param_file}")
                return False
            launcher = cls(param_file=param_file)
            logging.info(f"Starting {cls.__name__} with parameters: {param_file}")
            return launcher.run()
        except Exception as e:
            logging.error(f"Exception in PythonLauncher: {e}")
            return False

def run_from_params(param_file):
    """
    Module-level entry point for the unified launcher wrapper.
    Calls PythonLauncher.run_from_params.
    """
    return PythonLauncher.run_from_params(param_file)
