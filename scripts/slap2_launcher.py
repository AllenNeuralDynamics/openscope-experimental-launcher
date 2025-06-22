#!/usr/bin/env python3
"""
SLAP2 experiment launcher with advanced metadata generation.

This script provides a SLAP2-specific launcher that extends BonsaiLauncher
with SLAP2-specific functionality for stimulus table generation and 
session.json creation using aind-data-schema.
"""

import os
import logging
from typing import Dict, List, Optional, Any
import sys

# Add the src directory to the path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, '..', 'src')
sys.path.insert(0, src_dir)

# Import the launcher and utilities
from openscope_experimental_launcher.launchers import BonsaiLauncher
from openscope_experimental_launcher.utils import stimulus_table


class SLAP2Launcher(BonsaiLauncher):
    """
    SLAP2 Experiment launcher that extends BonsaiLauncher with SLAP2-specific functionality.
    
    Provides:
    - SLAP2-specific parameter handling
    - Automated stimulus table generation
    - Inherits session.json creation from base class
    """
    
    def __init__(self):
        """Initialize the SLAP2 experiment with additional session tracking."""
        super().__init__()
        
        # SLAP2-specific variables
        self.stimulus_table = None
        self.stimulus_table_path = None
        
        # Additional session parameters for SLAP2
        self.session_type = "SLAP2"
        
        logging.info("SLAP2 experiment launcher initialized")
    
    def _get_launcher_type_name(self) -> str:
        """Get the name of the experiment type for logging."""
        return "SLAP2"
    
    def post_experiment_processing(self) -> bool:
        """
        Perform SLAP2-specific post-experiment processing.
        
        This includes:
        - Stimulus table generation
        - Standard session.json creation (using base class)
        
        Returns:
            True if successful, False otherwise
        """
        logging.info("Starting SLAP2 post-experiment processing...")
        
        try:
            # Generate stimulus table (SLAP2-specific)
            if not self._generate_stimulus_table():
                logging.error("Failed to generate stimulus table")
                return False
            
            # Session.json creation is already handled by base class in the main run() method
            # No need to duplicate it here
            
            logging.info("SLAP2 post-experiment processing completed successfully")
            return True
            
        except Exception as e:
            logging.error(f"SLAP2 post-experiment processing failed: {e}")
            return False
    
    def _generate_stimulus_table(self) -> bool:
        """
        Generate stimulus presentation table for SLAP2 experiments.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logging.info("Generating SLAP2 stimulus table...")
            
            # Get stimulus parameters from experiment params
            stimulus_params = self.params.get('stimulus_parameters', {})
            
            # Generate stimulus table using utility
            self.stimulus_table = stimulus_table.generate_slap2_stimulus_table(
                stimulus_params=stimulus_params,
                session_info={
                    'subject_id': self.subject_id,
                    'session_uuid': self.session_uuid,
                    'field_of_view_id': self.params.get('field_of_view_id', 'FOV001')
                }
            )
              # Save stimulus table to output directory
            if self.output_session_folder:
                self.stimulus_table_path = os.path.join(
                    self.output_session_folder, 
                    'stimulus_table.csv'
                )
                self.stimulus_table.to_csv(self.stimulus_table_path, index=False)
                logging.info(f"Stimulus table saved to: {self.stimulus_table_path}")
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to generate stimulus table: {e}")
            return False


def main():
    """Main entry point for SLAP2 launcher."""
    if __name__ == "__main__":
        return SLAP2Launcher.main(
            description="Launch SLAP2 experiment with advanced metadata generation"
        )


if __name__ == "__main__":
    sys.exit(main())
