"""
SLAP2 experiment launcher with advanced metadata generation.

This module provides the SLAP2Experiment class that extends BaseExperiment
with SLAP2-specific functionality for stimulus table generation and 
session.json creation using aind-data-schema.
"""

import os
import logging
from typing import Dict, List, Optional, Any
import sys

# Import aind-data-schema components
try:
    from aind_data_schema.core.session import Session
    AIND_SCHEMA_AVAILABLE = True
except ImportError:
    AIND_SCHEMA_AVAILABLE = False
    logging.warning("aind-data-schema modules not available. Session.json creation will be disabled.")

from ..base.experiment import BaseExperiment
from .session_builder import SLAP2SessionBuilder
from .stimulus_table import SLAP2StimulusTableGenerator


class SLAP2Experiment(BaseExperiment):
    """
    SLAP2 Experiment launcher that extends BaseExperiment with SLAP2-specific functionality.
    
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
        self.rig_id = "slap2_rig"
        self.experimenter_name = "Unknown"  # Initialize with default for backwards compatibility
        
        # Initialize SLAP2 utility classes
        self.session_builder = SLAP2SessionBuilder()
        self.stimulus_table_generator = SLAP2StimulusTableGenerator()
        
        logging.info("SLAP2 Bonsai Experiment initialized")
    
    def collect_runtime_information(self) -> Dict[str, str]:
        """
        Collect key information from user at runtime.
        Extended for SLAP2-specific information.
        
        Returns:
            Dictionary containing collected runtime information
        """
        # Call parent method to get base information (subject_id and experimenter_name)
        runtime_info = super().collect_runtime_information()
        
        # Only collect rig_id if not already provided in params
        if not self.params.get("rig_id"):
            # Get default rig_id from platform info
            default_rig_id = self.platform_info.get('rig_id', 'slap2_rig')
            
            # Collect rig_id with clear default shown
            try:
                rig_id = input(f"Enter rig ID (default: {default_rig_id}): ").strip()
                if not rig_id:
                    rig_id = default_rig_id
            except (EOFError, OSError):
                # Handle cases where input is not available (e.g., during testing)
                rig_id = default_rig_id
            runtime_info["rig_id"] = rig_id
            
            logging.info(f"Collected SLAP2 runtime info - Rig: {rig_id}")
        
        return runtime_info

    def load_parameters(self, param_file: Optional[str]):
        """
        Load parameters from JSON file and extract SLAP2-specific parameters.
        
        Args:
            param_file: Path to the JSON parameter file
        """        # Call parent method to load base parameters (which includes runtime collection)
        super().load_parameters(param_file)
        
        # Extract SLAP2-specific parameters from loaded params (runtime info is already merged)
        self.session_type = self.params.get("session_type", "SLAP2")
        self.rig_id = self.params.get("rig_id", "slap2_rig")
        self.experimenter_name = self.params.get("experimenter_name", "Unknown")
        logging.info("SLAP2 parameters loaded successfully")
    
    def create_stimulus_table(self) -> bool:
        """
        Create a stimulus table from Bonsai output or trial parameters.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate stimulus table using the specialized generator
            self.stimulus_table = self.stimulus_table_generator.generate_stimulus_table(
                self.params, 
                self.session_output_path
            )
            
            if self.stimulus_table is not None:
                # Save stimulus table
                self.stimulus_table_path = os.path.join(
                    os.path.dirname(self.session_output_path),
                    os.path.splitext(os.path.basename(self.session_output_path))[0] + "_stimulus_table.csv"
                )
                
                self.stimulus_table.to_csv(self.stimulus_table_path, index=False)
                logging.info(f"Stimulus table saved to: {self.stimulus_table_path}")
                
                return True
            else:
                logging.error("Failed to generate stimulus table")
                return False
            
        except Exception as e:
            logging.error(f"Failed to create stimulus table: {e}")
            return False
    
    def create_session_json(self) -> bool:
        """
        Create a session.json file using aind-data-schema.
        
        Returns:
            True if successful, False otherwise
        """
        if not AIND_SCHEMA_AVAILABLE:
            logging.warning("aind-data-schema not available, skipping session.json creation")
            return False
        
        try:
            # Create session using the specialized builder
            session = self.session_builder.build_session(
                start_time=self.start_time,
                end_time=self.stop_time,
                params=self.params,
                mouse_id=self.mouse_id,
                user_id=self.user_id,
                experimenter_name=self.experimenter_name,
                session_uuid=self.session_uuid,
                slap_fovs=self.slap_fovs
            )
            
            if session:
                # Save session.json - fix the file path to avoid duplicate "session"
                base_name = os.path.splitext(os.path.basename(self.session_output_path))[0]
                output_dir = os.path.dirname(self.session_output_path)
                
                # Use write_standard_file correctly
                session.write_standard_file(
                    output_directory=output_dir,
                    prefix=base_name
                )
                
                # Set the correct path for verification
                self.session_json_path = os.path.join(output_dir, f"{base_name}_session.json")
                
                logging.info(f"Session.json saved to: {self.session_json_path}")
                return True
            else:
                logging.error("Failed to build session object")
                return False
            
        except Exception as e:
            logging.error(f"Failed to create session.json: {e}")
            return False
    
    def _get_experiment_type_name(self) -> str:
        """Get the experiment type name for SLAP2."""
        return "SLAP2"
    
    def post_experiment_processing(self) -> bool:
        """
        Perform post-experiment processing specific to SLAP2:
        1. Create stimulus table
        2. Create session.json file
        
        Returns:
            True if successful, False otherwise
        """
        logging.info("Starting SLAP2 post-experiment processing...")
        
        success = True
        
        # Create stimulus table
        if not self.create_stimulus_table():
            logging.error("Failed to create stimulus table")
            success = False
        
        # Create session.json file
        if not self.create_session_json():
            logging.error("Failed to create session.json file")
            success = False
        
        if success:
            logging.info("SLAP2 post-experiment processing completed successfully")
        else:
            logging.error("SLAP2 post-experiment processing completed with errors")
        
        return success
      # Remove the unnecessary run method override - the base class handles this correctly
    # The base class already calls post_experiment_processing() which we've properly overridden


def main():
    """Main function to run the SLAP2 Bonsai experiment."""
    logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s' )
    # Check if aind-data-schema is available
    if not AIND_SCHEMA_AVAILABLE:
        print("Warning: aind-data-schema is not installed. Session.json creation will be disabled.")
        print("To install: pip install aind-data-schema")
    
    # Get parameter file from command line
    param_file = None
    if len(sys.argv) > 1:
        param_file = sys.argv[1]
        if not os.path.exists(param_file):
            print(f"Error: Parameter file not found: {param_file}")
            sys.exit(1)
    
    # Create and run experiment
    experiment = SLAP2Experiment()
    
    try:
        success = experiment.run(param_file)
        if success:
            print("\n===== SLAP2 EXPERIMENT COMPLETED SUCCESSFULLY =====")
            if experiment.stimulus_table_path:
                print(f"Stimulus table: {experiment.stimulus_table_path}")
            if experiment.session_json_path:
                print(f"Session metadata: {experiment.session_json_path}")
            print(f"Experiment data: {experiment.output_path}")
            print("================================================\n")
            sys.exit(0)
        else:
            print("\n===== SLAP2 EXPERIMENT FAILED =====")
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