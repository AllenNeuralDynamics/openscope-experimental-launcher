#!/usr/bin/env python3
"""
Predictive Processing experiment launcher.

This script provides a launcher for the OpenScope Predictive Processing
project experiments using the new experimental launcher architecture.

Usage:
    python predictive_processing_launcher.py [path_to_parameters.json]
"""
import sys
import logging
from openscope_experimental_launcher.launchers import BonsaiLauncher
from openscope_experimental_launcher.post_processing import pp_stimulus_converter

class PredictiveProcessingLauncher(BonsaiLauncher):
    """
    Predictive Processing experiment launcher that extends BonsaiLauncher.
    
    This launcher provides functionality specific to the OpenScope
    Predictive Processing project experiments.
    """
    
    def __init__(self, param_file=None, rig_config_path=None):
        """Initialize the predictive processing experiment launcher."""
        super().__init__(param_file, rig_config_path)
        logging.info("Predictive Processing experiment launcher initialized")
    
    def _get_launcher_type_name(self) -> str:
        """Get the name of the experiment type for logging."""
        return "PredictiveProcessing"
    
    @staticmethod
    def run_post_processing(session_directory: str) -> bool:
        """
        Run post-processing for Predictive Processing experiments.
        Calls the parent BonsaiLauncher post-processing, then runs the
        dedicated stimulus table converter tool.
        
        Args:
            session_directory: Path to the session directory containing experiment data
            
        Returns:
            True if successful, False otherwise
        """
        logging.info("Starting Predictive Processing post-processing...")
        
        # Call parent post-processing (BonsaiLauncher)
        parent_success = BonsaiLauncher.run_post_processing(session_directory)
        if not parent_success:
            logging.warning("Parent post-processing failed")
        
        # Call the focused stimulus table converter
        logging.info("Running stimulus table converter...")
        stimulus_success = pp_stimulus_converter.convert_orientation_to_stimulus_table(session_directory)
        if not stimulus_success:
            logging.error("Stimulus table conversion failed")
        
        success = parent_success and stimulus_success
        if success:
            logging.info("Predictive Processing post-processing completed successfully")
        else:
            logging.error("Predictive Processing post-processing failed")
        
        return success


if __name__ == "__main__":
    sys.exit(PredictiveProcessingLauncher.main(
        description="Launch OpenScope Predictive Processing experiment"
    ))
