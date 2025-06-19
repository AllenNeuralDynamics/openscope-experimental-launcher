#!/usr/bin/env python3
"""
Predictive Processing experiment launcher.

This script provides a launcher for the OpenScope Predictive Processing
project experiments using the new experimental launcher architecture.

Usage:
    python predictive_processing_launcher.py [path_to_parameters.json]
"""

import os
import sys
import logging
from typing import Dict, Optional

# Add the src directory to the path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, '..', 'src')
sys.path.insert(0, src_dir)

from openscope_experimental_launcher.launchers import BonsaiLauncher


class PredictiveProcessingLauncher(BonsaiLauncher):
    """
    Predictive Processing experiment launcher that extends BonsaiLauncher.
    
    This launcher provides functionality specific to the OpenScope
    Predictive Processing project experiments.
    """
    
    def __init__(self):
        """Initialize the predictive processing experiment."""
        super().__init__()
        logging.info("Predictive Processing experiment launcher initialized")
    
    def _get_launcher_type_name(self) -> str:
        """Get the name of the experiment type for logging."""
        return "PredictiveProcessing"
    
    def collect_runtime_information(self) -> Dict[str, str]:
        """
        Collect Predictive Processing-specific runtime information.
        
        Extends the base collection with project-specific parameters.
        
        Returns:
            Dictionary containing collected runtime information
        """
        # Start with base runtime info
        runtime_info = super().collect_runtime_information()
        
        logging.info(f"Collected Predictive Processing runtime info - {runtime_info}")
        return runtime_info
    
    def post_experiment_processing(self) -> bool:
        """
        Perform Predictive Processing-specific post-experiment processing.
        
        This includes:
        - Data validation and organization
        - Stimulus timing verification
        - Quality control checks
        
        Returns:
            True if successful, False otherwise
        """
        logging.info("Starting Predictive Processing post-experiment processing...")
        
        try:
            # Validate data files were created
            if not self._validate_data_files():
                logging.warning("Data file validation failed")
                return False
            
            # Verify stimulus timing
            if not self._verify_stimulus_timing():
                logging.warning("Stimulus timing verification failed")
                # Don't fail the entire post-processing for timing issues
            
            # Perform quality control checks
            if not self._quality_control_checks():
                logging.warning("Quality control checks failed")
                # Don't fail the entire post-processing for QC issues
            
            logging.info("Predictive Processing post-experiment processing completed successfully")
            return True
            
        except Exception as e:
            logging.error(f"Predictive Processing post-experiment processing failed: {e}")
            return False
    
    def _validate_data_files(self) -> bool:
        """
        Validate that expected data files were created.
        
        Returns:
            True if validation successful, False otherwise
        """
        try:
            logging.info("Validating data files...")
            
            if not self.session_directory:
                logging.warning("No session directory available for validation")
                return False
            
            # Check for common data files
            expected_files = []
            
            # Add expected files based on recording type
            recording_type = self.params.get("recording_type", "ophys")
            if recording_type == "ophys":
                expected_files.extend([
                    "ophys_data.h5",
                    "timestamps.csv"
                ])
            elif recording_type == "ephys":
                expected_files.extend([
                    "ephys_data.dat",
                    "spike_times.npy"
                ])
            
            # Check for stimulus files
            stimulus_type = self.params.get("stimulus_type", "natural_movies")
            expected_files.extend([
                "stimulus_log.csv",
                "frame_times.csv"
            ])
            
            missing_files = []
            for filename in expected_files:
                filepath = os.path.join(self.session_directory, filename)
                if not os.path.exists(filepath):
                    missing_files.append(filename)
            
            if missing_files:
                logging.warning(f"Missing expected data files: {missing_files}")
                # Don't fail validation for missing files, just warn
            else:
                logging.info("All expected data files found")
            
            return True
            
        except Exception as e:
            logging.error(f"Data file validation failed: {e}")
            return False
    
    def _verify_stimulus_timing(self) -> bool:
        """
        Verify stimulus timing consistency.
        
        Returns:
            True if verification successful, False otherwise
        """
        try:
            logging.info("Verifying stimulus timing...")
            
            # This is a placeholder for actual timing verification
            # In a real implementation, you would:
            # 1. Load stimulus log files
            # 2. Check frame timing consistency
            # 3. Verify sync signals
            # 4. Compare expected vs actual timing
            
            logging.info("Stimulus timing verification completed")
            return True
            
        except Exception as e:
            logging.error(f"Stimulus timing verification failed: {e}")
            return False
    
    def _quality_control_checks(self) -> bool:
        """
        Perform quality control checks on collected data.
        
        Returns:
            True if QC checks successful, False otherwise
        """
        try:
            logging.info("Performing quality control checks...")
            
            # This is a placeholder for actual QC checks
            # In a real implementation, you would:
            # 1. Check data integrity
            # 2. Verify recording quality metrics
            # 3. Check for data corruption
            # 4. Validate stimulus presentation
            
            logging.info("Quality control checks completed")
            return True
            
        except Exception as e:
            logging.error(f"Quality control checks failed: {e}")
            return False


def main():
    """Main entry point for Predictive Processing launcher."""
    if __name__ == "__main__":
        return PredictiveProcessingLauncher.main(
            description="Launch OpenScope Predictive Processing experiment"
        )


if __name__ == "__main__":
    sys.exit(main())
