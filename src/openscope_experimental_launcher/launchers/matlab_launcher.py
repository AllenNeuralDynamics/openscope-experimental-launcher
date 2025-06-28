"""
MATLAB launcher for OpenScope experiments.

This module provides a launcher for running MATLAB scripts.
"""

import os
import subprocess
import logging
from .base_launcher import BaseLauncher
from ..interfaces import matlab_interface
from ..utils import git_manager


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

    @classmethod
    def run_from_params(cls, param_file):
        """
        Run the experiment with the specified parameters (MATLAB version).
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
            logging.error(f"Exception in MatlabLauncher: {e}")
            return False

def run_from_params(param_file):
    """
    Module-level entry point for the unified launcher wrapper.
    Calls MatlabLauncher.run_from_params.
    """
    return MatlabLauncher.run_from_params(param_file)
