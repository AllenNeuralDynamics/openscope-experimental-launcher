#!/usr/bin/env python3
"""
Example Python launcher for OpenScope experiments.

This script demonstrates how to create a Python-based experiment launcher
using the new experimental launcher architecture.

Usage:
    python example_python_launcher.py [path_to_parameters.json]
"""

import os
import sys
import logging

# Add the src directory to the path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, '..', 'src')
sys.path.insert(0, src_dir)

from openscope_experimental_launcher.launchers import PythonLauncher


class ExamplePythonLauncher(PythonLauncher):
    """
    Example Python experiment launcher.
    
    This demonstrates how to extend PythonLauncher for specific experiments.
    """
    
    def __init__(self):
        """Initialize the example Python experiment."""
        super().__init__()
        logging.info("Example Python experiment launcher initialized")
    
    def _get_launcher_type_name(self) -> str:
        """Get the name of the experiment type for logging."""
        return "ExamplePython"
    
    def post_experiment_processing(self) -> bool:
        """
        Perform example post-experiment processing.
        
        Returns:
            True if successful, False otherwise
        """
        logging.info("Starting example Python post-experiment processing...")
        
        try:
            # Example: check for output files
            if self.session_directory:
                python_files = [f for f in os.listdir(self.session_directory) 
                              if f.endswith(('.pkl', '.npy', '.csv'))]
                logging.info(f"Found {len(python_files)} Python output files")
            
            logging.info("Example Python post-experiment processing completed successfully")
            return True
            
        except Exception as e:
            logging.error(f"Example Python post-experiment processing failed: {e}")
            return False


def main():
    """Main entry point for example Python launcher."""
    if __name__ == "__main__":
        return ExamplePythonLauncher.main(
            description="Launch example Python-based OpenScope experiment"
        )


if __name__ == "__main__":
    sys.exit(main())
