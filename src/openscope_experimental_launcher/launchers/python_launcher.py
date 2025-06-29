"""
Python launcher for OpenScope experiments.

This module provides a launcher for running Python scripts.
"""

import subprocess
from .base_launcher import BaseLauncher
from ..interfaces import python_interface


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

def run_from_params(param_file):
    """
    Module-level entry point for the unified launcher wrapper.
    Calls PythonLauncher.run_from_params.
    """
    return PythonLauncher.run_from_params(param_file)