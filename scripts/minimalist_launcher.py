#!/usr/bin/env python3
"""
Minimalist test launcher for openscope-experimental-launcher.

This is a simple test script that extends BaseLauncher with minimal
functionality - it demonstrates the base launcher capabilities without
running any actual processes.

Usage:
    python minimalist_launcher.py [path_to_parameters.json]
"""

import os
import sys
import logging
import subprocess
from typing import Optional, List

# Add the src directory to the path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, '..', 'src')
sys.path.insert(0, src_dir)

from openscope_experimental_launcher.launchers import BaseLauncher


class MinimalistLauncher(BaseLauncher):
    """
    Minimalist test experiment launcher that uses BaseLauncher directly.
    
    This launcher provides minimal functionality to test BaseLauncher:
    - Loads parameters from JSON
    - Sets up the repository
    - Creates a mock process (doesn't actually run anything)
    - Demonstrates all base launcher features without external dependencies
    """
    
    def __init__(self):
        """Initialize the test experiment."""
        super().__init__()
        logging.info("Minimalist test experiment initialized")
    
    def _get_launcher_type_name(self) -> str:
        """Get the name of the experiment type for logging."""
        return "MinimalistTest"
    
    def create_process(self) -> subprocess.Popen:
        """
        Create a mock process for testing BaseLauncher functionality.
        
        This method creates a simple process that runs a basic command
        to demonstrate the BaseLauncher process management without
        requiring external dependencies like Bonsai or MATLAB.
        
        Returns:
            subprocess.Popen object for a simple test process
        """

        # Get the script path from parameters
        script_path = self.params.get('script_path', 'echo')
        
        # Create a simple command that will run successfully
        if script_path == 'echo' or not script_path:
            # Default: just echo a test message
            cmd = ['python', '-c', 
                   f'print("MinimalistLauncher test process running for subject: {self.subject_id}"); '
                   f'import time; time.sleep(2); '
                   f'print("MinimalistLauncher test process completed successfully")']
        else:
            # If a script path is provided, try to run it as a Python script
            cmd = ['python', script_path]
        
        logging.info(f"Creating test process with command: {' '.join(cmd)}")
        
        # Create the process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.output_session_folder or os.getcwd()
        )
        
        logging.info(f"Test process created with PID: {process.pid}")
        return process
    
    def post_experiment_processing(self) -> bool:
        """
        No post-experiment processing for the minimalist launcher.
        Just log completion and return success.
        
        Returns:
            True (always successful since we do nothing)
        """
        logging.info("Minimalist test experiment completed - no post-processing required")
        return True


def main():
    """Main entry point for minimalist launcher."""
    if __name__ == "__main__":
        return MinimalistLauncher.main(
            description="Test BaseLauncher functionality with minimal mock process"
        )


if __name__ == "__main__":
    sys.exit(main())
