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
    - Session.json creation using aind-data-schema
    - SLAP field of view management
    """
    
    def __init__(self):
        """Initialize the SLAP2 experiment with additional session tracking."""
        super().__init__()
        
        # SLAP2-specific variables
        self.stimulus_table = None
        self.session_metadata = None
        self.slap_fovs = []
        self.trial_data = []
        self.session_json_path = None
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
        - Session.json creation using aind-data-schema
        - FOV metadata collection
        
        Returns:
            True if successful, False otherwise
        """
        logging.info("Starting SLAP2 post-experiment processing...")
        
        try:
            # Generate stimulus table
            if not self._generate_stimulus_table():
                logging.warning("Failed to generate stimulus table")
                return False
            
            # Create session.json using aind-data-schema
            if not self._create_session_json():
                logging.warning("Failed to create session.json")
                return False
            
            # Process field of view data if available
            if not self._process_fov_data():
                logging.warning("Failed to process FOV data")
                # Don't fail the entire post-processing for FOV issues
            
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

    def _create_session_json(self) -> bool:
        """
        Create session.json file using the base class functionality.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logging.info("Creating session.json using base class method...")
              # Use the base class method to create session.json
            if self.output_session_folder:
                return self.create_session_file(self.output_session_folder)
            else:
                logging.warning("No output session folder set, skipping session.json creation")
                return True
            
        except Exception as e:
            logging.error(f"Failed to create session.json: {e}")
            return False
    
    def _process_fov_data(self) -> bool:
        """
        Process field of view specific data for SLAP2.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logging.info("Processing SLAP2 field of view data...")
            
            # Extract FOV information from parameters
            fov_id = self.params.get('field_of_view_id', 'FOV001')
            imaging_depth = self.params.get('imaging_depth', 200)
            
            # Store FOV data
            fov_data = {
                'fov_id': fov_id,
                'imaging_depth_um': imaging_depth,
                'session_uuid': self.session_uuid,
                'timestamp': self.start_time.isoformat() if self.start_time else None
            }
            
            self.slap_fovs.append(fov_data)
              # Save FOV metadata if output directory exists
            if self.output_session_folder:
                fov_metadata_path = os.path.join(
                    self.output_session_folder,
                    'fov_metadata.json'
                )
                
                import json
                with open(fov_metadata_path, 'w') as f:
                    json.dump({'fields_of_view': self.slap_fovs}, f, indent=2)
                
                logging.info(f"FOV metadata saved to: {fov_metadata_path}")
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to process FOV data: {e}")
            return False


def main():
    """Main entry point for SLAP2 launcher."""
    if __name__ == "__main__":
        return SLAP2Launcher.main(
            description="Launch SLAP2 experiment with advanced metadata generation"
        )


if __name__ == "__main__":
    sys.exit(main())
