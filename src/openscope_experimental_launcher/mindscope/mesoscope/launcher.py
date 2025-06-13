"""
Mindscope Mesoscope rig experiment launcher.

This module provides the MesoscopeExperiment class that extends BaseExperiment
with mesoscope-specific functionality for pickle file generation.
"""

import os
import pickle
import logging
import datetime
from typing import Dict, List, Optional, Any

from ...base.experiment import BaseExperiment


class MesoscopeExperiment(BaseExperiment):
    """
    Mesoscope rig experiment launcher that extends BaseExperiment.
    
    Provides mesoscope-specific functionality including:
    - Pickle file generation for downstream pipeline
    - Mesoscope-specific parameter handling
    - Multi-plane imaging configuration
    """
    
    def __init__(self):
        """Initialize the mesoscope experiment."""
        super().__init__()
        self.rig_type = "mesoscope"
        self.pickle_file_path = None
        self.imaging_planes = []
        logging.info("Mesoscope experiment initialized")
    
    def load_parameters(self, param_file: Optional[str]):
        """
        Load parameters and extract mesoscope-specific configuration.
        
        Args:
            param_file: Path to the JSON parameter file
        """
        # Call parent method to load base parameters
        super().load_parameters(param_file)
        
        # Extract mesoscope-specific parameters
        self.imaging_planes = self.params.get("imaging_planes", [])
        if self.imaging_planes:
            logging.info(f"Configured {len(self.imaging_planes)} imaging planes")
        
        # Log mesoscope-specific configuration
        zoom_level = self.params.get("zoom_level")
        if zoom_level:
            logging.info(f"Mesoscope zoom level: {zoom_level}")
    
    def post_experiment_processing(self) -> bool:
        """
        Perform mesoscope-specific post-experiment processing:
        Generate pickle file for downstream pipeline.
        
        Returns:
            True if successful, False otherwise
        """
        logging.info("Starting mesoscope-specific post-experiment processing...")
        
        try:
            # Generate pickle file
            if not self.create_pickle_file():
                logging.error("Failed to create pickle file")
                return False
            
            logging.info("Mesoscope post-experiment processing completed successfully")
            return True
            
        except Exception as e:
            logging.error(f"Mesoscope post-experiment processing failed: {e}")
            return False
    
    def create_pickle_file(self) -> bool:
        """
        Create a pickle file containing experiment metadata and mesoscope-specific parameters.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create pickle file path
            if self.session_output_path:
                base_name = os.path.splitext(self.session_output_path)[0]
                self.pickle_file_path = f"{base_name}_mesoscope_metadata.pkl"
            else:
                # Fallback naming
                dt_str = datetime.datetime.now().strftime('%y%m%d%H%M%S')
                self.pickle_file_path = f"mesoscope_experiment_{dt_str}.pkl"
            
            # Prepare data for pickle file
            pickle_data = {
                'rig_type': self.rig_type,
                'session_uuid': self.session_uuid,
                'mouse_id': self.mouse_id,
                'user_id': self.user_id,
                'start_time': self.start_time,
                'stop_time': self.stop_time,
                'parameters': self.params,
                'platform_info': self.platform_info,
                'script_checksum': self.script_checksum,
                'params_checksum': self.params_checksum,
                'session_output_path': self.session_output_path,
                'bonsai_stdout': self.stdout_data if hasattr(self, 'stdout_data') else [],
                'bonsai_stderr': self.stderr_data if hasattr(self, 'stderr_data') else [],
                'hardware_config': self.config,
                'mesoscope_specific': {
                    'processing_timestamp': datetime.datetime.now(),
                    'pickle_version': '1.0',
                    'data_format': 'mesoscope_mindscope',
                    'imaging_planes': self.imaging_planes,
                    'zoom_level': self.params.get('zoom_level'),
                    'objective': self.params.get('objective'),
                    'pixel_size_um': self.params.get('pixel_size_um'),
                    'frame_rate_hz': self.params.get('frame_rate_hz'),
                    'excitation_wavelength_nm': self.params.get('excitation_wavelength_nm'),
                    'emission_filter': self.params.get('emission_filter')
                }
            }
            
            # Add duration if available
            if self.start_time and self.stop_time:
                pickle_data['duration_seconds'] = (self.stop_time - self.start_time).total_seconds()
            
            # Add imaging plane statistics
            if self.imaging_planes:
                pickle_data['mesoscope_specific']['num_planes'] = len(self.imaging_planes)
                pickle_data['mesoscope_specific']['plane_depths'] = [
                    plane.get('depth_um', 0) for plane in self.imaging_planes
                ]
            
            # Save pickle file
            with open(self.pickle_file_path, 'wb') as f:
                pickle.dump(pickle_data, f)
            
            logging.info(f"Mesoscope pickle file saved to: {self.pickle_file_path}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to create mesoscope pickle file: {e}")
            return False
    
    def get_pickle_data_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the mesoscope data that will be saved in the pickle file.
        
        Returns:
            Dictionary containing data summary
        """
        if not self.pickle_file_path or not os.path.exists(self.pickle_file_path):
            return {'error': 'Pickle file not found'}
        
        try:
            with open(self.pickle_file_path, 'rb') as f:
                data = pickle.load(f)
            
            mesoscope_data = data.get('mesoscope_specific', {})
            summary = {
                'rig_type': data.get('rig_type'),
                'session_uuid': data.get('session_uuid'),
                'mouse_id': data.get('mouse_id'),
                'duration_seconds': data.get('duration_seconds'),
                'num_parameters': len(data.get('parameters', {})),
                'num_imaging_planes': mesoscope_data.get('num_planes', 0),
                'zoom_level': mesoscope_data.get('zoom_level'),
                'frame_rate_hz': mesoscope_data.get('frame_rate_hz'),
                'has_stdout': len(data.get('bonsai_stdout', [])) > 0,
                'has_stderr': len(data.get('bonsai_stderr', [])) > 0,
                'pickle_file_size_bytes': os.path.getsize(self.pickle_file_path)
            }
            
            return summary
            
        except Exception as e:
            return {'error': f'Failed to read pickle file: {e}'}


def main():
    """Main function to run the mesoscope experiment."""
    import sys
    
    # Get parameter file from command line
    param_file = None
    if len(sys.argv) > 1:
        param_file = sys.argv[1]
        if not os.path.exists(param_file):
            print(f"Error: Parameter file not found: {param_file}")
            sys.exit(1)
    
    # Create and run experiment
    experiment = MesoscopeExperiment()
    
    try:
        success = experiment.run(param_file)
        if success:
            print("\n===== MESOSCOPE EXPERIMENT COMPLETED SUCCESSFULLY =====")
            if experiment.pickle_file_path:
                print(f"Pickle file: {experiment.pickle_file_path}")
                summary = experiment.get_pickle_data_summary()
                print(f"Data summary: {summary}")
            print(f"Experiment data: {experiment.session_output_path}")
            print("======================================================\n")
            sys.exit(0)
        else:
            print("\n===== MESOSCOPE EXPERIMENT FAILED =====")
            print("Check the logs above for error details.")
            print("======================================\n")
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