#!/usr/bin/env python3
"""
Example MATLAB launcher for OpenScope experiments.

This script demonstrates how to create a MATLAB-based experiment launcher
using the new experimental launcher architecture.

Usage:
    python example_matlab_launcher.py [path_to_parameters.json]
"""

import os
import sys
import logging

# Add the src directory to the path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, '..', 'src')
sys.path.insert(0, src_dir)

from openscope_experimental_launcher.launchers import MatlabLauncher


class ExampleMatlabLauncher(MatlabLauncher):
    """
    Example MATLAB experiment launcher.
    
    This demonstrates how to extend MatlabLauncher for specific experiments.
    """
    
    def __init__(self):
        """Initialize the example MATLAB experiment."""
        super().__init__()
        logging.info("Example MATLAB experiment launcher initialized")
    
    def _get_launcher_type_name(self) -> str:
        """Get the name of the experiment type for logging."""
        return "ExampleMATLAB"
    
    def post_experiment_processing(self) -> bool:
        """
        Perform example post-experiment processing.
        
        Returns:
            True if successful, False otherwise
        """
        logging.info("Starting example MATLAB post-experiment processing...")
        
        try:
            # Example: check for output files
            if self.session_directory:
                output_files = [f for f in os.listdir(self.session_directory) if f.endswith('.mat')]
                logging.info(f"Found {len(output_files)} .mat output files")
            
            logging.info("Example MATLAB post-experiment processing completed successfully")
            return True
            
        except Exception as e:
            logging.error(f"Example MATLAB post-experiment processing failed: {e}")
            return False


def main():
    """Main entry point for example MATLAB launcher."""
    if __name__ == "__main__":
        return ExampleMatlabLauncher.main(
            description="Launch example MATLAB-based OpenScope experiment"
        )


if __name__ == "__main__":
    sys.exit(main())
