"""
MATLAB launcher for OpenScope experiments.

This module provides a launcher for running MATLAB scripts.
"""

import subprocess
from .base_launcher import BaseLauncher
from ..interfaces import matlab_interface


class MatlabLauncher(BaseLauncher):
    """
    Launcher for MATLAB-based OpenScope experiments.
    Extends BaseLauncher with MATLAB-specific process creation.
    """
    
    def _get_launcher_type_name(self) -> str:
        """Get the name of the launcher type for logging."""
        return "MATLAB"
    
    def create_process(self) -> subprocess.Popen:
        """
        Create the MATLAB subprocess.
        
        Returns:
            subprocess.Popen object for the running MATLAB script
        """
        # Setup MATLAB environment
        if not matlab_interface.setup_matlab_environment(self.params):
            raise RuntimeError("Failed to setup MATLAB environment")
        
        # Get script path
        script_path = self._get_script_path()
        
        # Construct arguments
        script_args = matlab_interface.construct_matlab_arguments(self.params)
        
        # Start MATLAB script
        matlab_exe_path = self.params.get('matlab_exe_path', 'matlab')
        process = matlab_interface.start_matlab_script(
            script_path=script_path,
            matlab_exe_path=matlab_exe_path,
            arguments=script_args,
            output_folder=self.output_session_folder
        )
        
        return process

def run_from_params(param_file):
    """
    Module-level entry point for the unified launcher wrapper.
    Calls MatlabLauncher.run_from_params.
    """
    return MatlabLauncher.run_from_params(param_file)