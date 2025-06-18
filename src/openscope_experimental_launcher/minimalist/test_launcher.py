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
    Minimalist test experiment launcher that uses BaseExperiment.
    
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


if __name__ == "__main__":
    TestExperiment.main("Launch minimalist test experiment")