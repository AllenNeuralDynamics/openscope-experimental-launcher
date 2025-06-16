"""
Mindscope Neuropixel rig experiment launcher.

This module provides the NeuropixelExperiment class that extends BaseExperiment
with neuropixel-specific functionality for pickle file generation.
"""

import os
import pickle
import logging
import datetime
from typing import Dict, List, Optional, Any

from ...base.experiment import BaseExperiment


class NeuropixelExperiment(BaseExperiment):
    """
    Neuropixel rig experiment launcher that extends BaseExperiment.
    
    Provides neuropixel-specific functionality including:
    - Pickle file generation for downstream pipeline
    - Neuropixel probe configuration
    - Multi-probe support
    - Electrophysiology-specific metadata
    """
    
    def __init__(self):
        """Initialize the neuropixel experiment."""
        super().__init__()
        self.rig_type = "neuropixel"
        self.pickle_file_path = None
        self.probes = []
        self.recording_channels = []
        logging.info("Neuropixel experiment initialized")
    
    def _get_experiment_type_name(self) -> str:
        """Get the experiment type name for Neuropixel."""
        return "Neuropixel"
    
    def load_parameters(self, param_file: Optional[str]):
        """
        Load parameters and extract neuropixel-specific configuration.
        
        Args:
            param_file: Path to the JSON parameter file
        """
        # Call parent method to load base parameters
        super().load_parameters(param_file)
        
        # Extract neuropixel-specific parameters
        self.probes = self.params.get("probes", [])
        self.recording_channels = self.params.get("recording_channels", [])
        
        if self.probes:
            logging.info(f"Configured {len(self.probes)} Neuropixel probes")
            for i, probe in enumerate(self.probes):
                probe_type = probe.get("type", "unknown")
                probe_id = probe.get("serial_number", f"probe_{i}")
                logging.info(f"  Probe {i}: {probe_type} (ID: {probe_id})")
        
        # Log recording configuration
        sampling_rate = self.params.get("sampling_rate_hz")
        if sampling_rate:
            logging.info(f"Neuropixel sampling rate: {sampling_rate} Hz")
    
    
    def post_experiment_processing(self) -> bool:
        """
        Perform neuropixel-specific post-experiment processing:
        Generate pickle file for downstream pipeline.
        
        Returns:
            True if successful, False otherwise
        """
        logging.info("Starting neuropixel-specific post-experiment processing...")
        
        try:
            # Generate pickle file
            if not self.create_pickle_file():
                logging.error("Failed to create pickle file")
                return False
            
            logging.info("Neuropixel post-experiment processing completed successfully")
            return True
            
        except Exception as e:
            logging.error(f"Neuropixel post-experiment processing failed: {e}")
            return False
    
    def create_pickle_file(self) -> bool:
        """
        Create a pickle file containing experiment metadata and neuropixel-specific parameters.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create pickle file path
            if self.session_output_path:
                base_name = os.path.splitext(self.session_output_path)[0]
                self.pickle_file_path = f"{base_name}_neuropixel_metadata.pkl"
            else:
                # Fallback naming
                dt_str = datetime.datetime.now().strftime('%y%m%d%H%M%S')
                self.pickle_file_path = f"neuropixel_experiment_{dt_str}.pkl"
            
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
                'neuropixel_specific': {
                    'processing_timestamp': datetime.datetime.now(),
                    'pickle_version': '1.0',
                    'data_format': 'neuropixel_mindscope',
                    'probes': self.probes,
                    'recording_channels': self.recording_channels,
                    'sampling_rate_hz': self.params.get('sampling_rate_hz'),
                    'gain_setting': self.params.get('gain_setting'),
                    'reference_channel': self.params.get('reference_channel'),
                    'ap_band_filter': self.params.get('ap_band_filter'),
                    'lfp_band_filter': self.params.get('lfp_band_filter'),
                    'spike_sorting_enabled': self.params.get('spike_sorting_enabled', False)
                }
            }
            
            # Add duration if available
            if self.start_time and self.stop_time:
                pickle_data['duration_seconds'] = (self.stop_time - self.start_time).total_seconds()
            
            # Add probe statistics
            if self.probes:
                pickle_data['neuropixel_specific']['num_probes'] = len(self.probes)
                pickle_data['neuropixel_specific']['probe_types'] = [
                    probe.get('type', 'unknown') for probe in self.probes
                ]
                pickle_data['neuropixel_specific']['probe_serials'] = [
                    probe.get('serial_number', 'unknown') for probe in self.probes
                ]
            
            # Add channel statistics
            if self.recording_channels:
                pickle_data['neuropixel_specific']['num_recording_channels'] = len(self.recording_channels)
                pickle_data['neuropixel_specific']['total_data_rate_mbps'] = self._estimate_data_rate()
            
            # Save pickle file
            with open(self.pickle_file_path, 'wb') as f:
                pickle.dump(pickle_data, f)
            
            logging.info(f"Neuropixel pickle file saved to: {self.pickle_file_path}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to create neuropixel pickle file: {e}")
            return False
    
    def _estimate_data_rate(self) -> float:
        """
        Estimate data rate based on sampling rate and number of channels.
        
        Returns:
            Estimated data rate in Mbps
        """
        try:
            sampling_rate = self.params.get('sampling_rate_hz', 30000)
            num_channels = len(self.recording_channels) if self.recording_channels else 384
            bits_per_sample = 16  # Typical for Neuropixel
            
            # Calculate data rate: samples/sec * channels * bits/sample * probes
            data_rate_bps = sampling_rate * num_channels * bits_per_sample * len(self.probes) if self.probes else 1
            data_rate_mbps = data_rate_bps / 1_000_000
            
            return round(data_rate_mbps, 2)
        except Exception:
            return 0.0
    
    def get_pickle_data_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the neuropixel data that will be saved in the pickle file.
        
        Returns:
            Dictionary containing data summary
        """
        if not self.pickle_file_path or not os.path.exists(self.pickle_file_path):
            return {'error': 'Pickle file not found'}
        
        try:
            with open(self.pickle_file_path, 'rb') as f:
                data = pickle.load(f)
            
            neuropixel_data = data.get('neuropixel_specific', {})
            summary = {
                'rig_type': data.get('rig_type'),
                'session_uuid': data.get('session_uuid'),
                'mouse_id': data.get('mouse_id'),
                'duration_seconds': data.get('duration_seconds'),
                'num_parameters': len(data.get('parameters', {})),
                'num_probes': neuropixel_data.get('num_probes', 0),
                'num_recording_channels': neuropixel_data.get('num_recording_channels', 0),
                'sampling_rate_hz': neuropixel_data.get('sampling_rate_hz'),
                'estimated_data_rate_mbps': neuropixel_data.get('total_data_rate_mbps'),
                'probe_types': neuropixel_data.get('probe_types', []),
                'has_stdout': len(data.get('bonsai_stdout', [])) > 0,
                'has_stderr': len(data.get('bonsai_stderr', [])) > 0,
                'pickle_file_size_bytes': os.path.getsize(self.pickle_file_path)
            }
            
            return summary
            
        except Exception as e:
            return {'error': f'Failed to read pickle file: {e}'}


def main():
    """Main function to run the neuropixel experiment."""
    import sys
    
    # Get parameter file from command line
    param_file = None
    if len(sys.argv) > 1:
        param_file = sys.argv[1]
        if not os.path.exists(param_file):
            print(f"Error: Parameter file not found: {param_file}")
            sys.exit(1)
    
    # Create and run experiment
    experiment = NeuropixelExperiment()
    
    try:
        success = experiment.run(param_file)
        if success:
            print("\n===== NEUROPIXEL EXPERIMENT COMPLETED SUCCESSFULLY =====")
            if experiment.pickle_file_path:
                print(f"Pickle file: {experiment.pickle_file_path}")
                summary = experiment.get_pickle_data_summary()
                print(f"Data summary: {summary}")
            print(f"Experiment data: {experiment.session_output_path}")
            print("========================================================\n")
            sys.exit(0)
        else:
            print("\n===== NEUROPIXEL EXPERIMENT FAILED =====")
            print("Check the logs above for error details.")
            print("========================================\n")
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