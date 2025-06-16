#!/usr/bin/env python3
"""
Minimalist test launcher for openscope-experimental-launcher.

This is a simple test launcher that extends BaseExperiment with minimal
functionality - it just runs the Bonsai workflow with no post-processing.

Usage:
    python test_launcher.py [path_to_parameters.json]
"""

import os
import sys
import logging
from typing import Optional, List

# Add the src directory to the path so we can import the base experiment
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from openscope_experimental_launcher.base.experiment import BaseExperiment


class TestExperiment(BaseExperiment):
    """
    Minimalist test experiment launcher that extends BaseExperiment.
    
    This launcher provides minimal functionality:
    - Loads parameters from JSON
    - Sets up the repository
    - Runs the Bonsai workflow
    - No post-processing (just runs and exits)
    - Custom Bonsai arguments to avoid property conflicts
    """
    
    def __init__(self):
        """Initialize the test experiment."""
        super().__init__()
        self.rig_type = "test"
        logging.info("Test experiment initialized")
    
    def post_experiment_processing(self) -> bool:
        """
        No post-experiment processing for the test launcher.
        Just log completion and return success.
        
        Returns:
            True (always successful since we do nothing)
        """
        logging.info("Test experiment completed - no post-processing required")
        return True


def main():
    """Main function to run the test experiment."""
    # Set up basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Get parameter file from command line
    param_file = None
    if len(sys.argv) > 1:
        param_file = sys.argv[1]
        if not os.path.exists(param_file):
            print(f"Error: Parameter file not found: {param_file}")
            sys.exit(1)
    else:
        # Use default parameter file if none provided
        default_params = os.path.join(os.path.dirname(__file__), "sample_params.json")
        if os.path.exists(default_params):
            param_file = default_params
            print(f"Using default parameter file: {param_file}")
        else:
            print("Error: No parameter file provided and no default found")
            print("Usage: python test_launcher.py [path_to_parameters.json]")
            sys.exit(1)
    
    # Create and run experiment
    experiment = TestExperiment()
    
    try:
        print(f"Starting test experiment with parameters: {param_file}")
        success = experiment.run(param_file)
        
        if success:
            print("\n===== TEST EXPERIMENT COMPLETED SUCCESSFULLY =====")
            print(f"Experiment data: {experiment.session_output_path}")
            print("==================================================\n")
            sys.exit(0)
        else:
            print("\n===== TEST EXPERIMENT FAILED =====")
            print("Check the logs above for error details.")
            print("===================================\n")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nExperiment interrupted by user")
        experiment.stop()
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        experiment.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()