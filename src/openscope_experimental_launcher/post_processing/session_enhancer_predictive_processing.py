#!/usr/bin/env python3
"""
Predictive Processing Session Enhancement Post-Processing Tool

This tool enhances existing session.json files by adding Predictive Processing-specific data streams
and stimulus epochs. It loads the base session.json created by the standard SessionCreator and adds:
1. SLAP2 imaging streams using timing data from HARP files
2. Stimulus epochs based on stimulus table phases (orientation tuning, oddball, receptive field)

This design avoids inheritance complexity and creates clear separation between
base session creation and Predictive Processing-specific enhancements.
"""

import json
import logging
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
from openscope_experimental_launcher.utils import param_utils

try:
    from aind_data_schema.core.session import Session, Stream, StimulusEpoch, SlapFieldOfView
    from aind_data_schema.components.devices import Software
    from aind_data_schema_models.modalities import Modality as StreamModality
    AIND_AVAILABLE = True
except ImportError:
    AIND_AVAILABLE = False

try:
    from .pp_stimulus_converter import get_timing_data
except ImportError:
    # Fallback for direct execution
    try:
        from openscope_experimental_launcher.post_processing.pp_stimulus_converter import get_timing_data
    except ImportError:
        get_timing_data = None


class PredictiveProcessingSessionEnhancer:
    """Enhance existing session.json files with Predictive Processing-specific information."""
    
    def __init__(self, output_folder: str):
        self.output_folder = Path(output_folder)
        self.session_file = self.output_folder / "session.json"
        self.harp_folder = self.output_folder / ".harp"
        self.stimulus_table_file = self.output_folder / "stimulus_table.csv"
        self.end_state_file = self.output_folder / "launcher_metadata" / "end_state.json"
    
    def enhance_session(self) -> bool:
        """
        Enhance session.json with Predictive Processing-specific data streams and stimulus epochs.
        
        Returns:
            True if enhancement successful, False otherwise
        """
        if not AIND_AVAILABLE:
            logging.error("aind-data-schema not available, cannot enhance session")
            return False
        
        if get_timing_data is None:
            logging.error("pp_stimulus_converter not available, cannot read HARP timing data")
            return False
        
        try:
            # Load existing session.json
            if not self.session_file.exists():
                logging.error(f"No session.json found at {self.session_file}")
                return False
            
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)
            
            # Convert to Session object for proper handling
            session = Session.model_validate(session_data)
            
            # Add SLAP2 streams
            slap2_streams = self._create_slap2_streams(session)
            if slap2_streams:
                if session.data_streams:
                    session.data_streams.extend(slap2_streams)
                else:
                    session.data_streams = slap2_streams
                logging.info(f"Added {len(slap2_streams)} SLAP2 streams")
            
            # Add stimulus epochs
            stimulus_epochs = self._create_stimulus_epochs(session)
            if stimulus_epochs:
                session.stimulus_epochs = stimulus_epochs
                logging.info(f"Added {len(stimulus_epochs)} stimulus epochs")
            
            # Update session type
            if session.session_type in ['Behavior', 'Generic', 'Unknown']:
                session.session_type = 'Predictive Processing'
            
            # Save enhanced session
            with open(self.session_file, 'w') as f:
                json.dump(session.model_dump(), f, indent=2, default=str)
            
            logging.info("Enhanced session with Predictive Processing data")
            return True
                
        except Exception as e:
            logging.error(f"Failed to enhance session: {e}")
            return False
    
    def _create_slap2_streams(self, session: Session) -> List[Stream]:
        """Create SLAP2 imaging data streams based on HARP timing data."""
        streams = []
        
        if not self.harp_folder.exists():
            logging.warning("No HARP folder found - skipping SLAP2 streams")
            return streams
        
        try:
            # Read HARP timing data
            timing_data = get_timing_data(self.harp_folder)
            if not timing_data or 'normalized_start_trial' not in timing_data:
                logging.warning("No valid timing data found - skipping SLAP2 streams")
                return streams
            
            start_times = timing_data['normalized_start_trial']
            end_times = timing_data['normalized_end_trial']
            
            if len(start_times) == 0 or len(end_times) == 0:
                logging.warning("No trial timing data found - skipping SLAP2 streams")
                return streams
            
            # Get overall SLAP2 imaging duration (first start to last end)
            slap2_start_offset = float(start_times[0])  # seconds from session start
            slap2_end_offset = float(end_times[-1])     # seconds from session start
            
            # Calculate absolute times
            slap2_start_time = session.session_start_time.replace(microsecond=0) + pd.Timedelta(seconds=slap2_start_offset)
            slap2_end_time = session.session_start_time.replace(microsecond=0) + pd.Timedelta(seconds=slap2_end_offset)
              # Create SLAP2 imaging stream
            slap2_stream = Stream(
                stream_start_time=slap2_start_time,
                stream_end_time=slap2_end_time,
                stream_modalities=[StreamModality.SLAP],
                daq_names=["SLAP2"],
                slap_fovs=[self._create_slap2_fov()]
            )
            
            streams.append(slap2_stream)
            logging.info(f"Created SLAP2 stream from {slap2_start_time} to {slap2_end_time}")
            
        except Exception as e:
            logging.error(f"Failed to create SLAP2 streams: {e}")        
        return streams
    
    def _create_slap2_fov(self) -> SlapFieldOfView:
        """Create placeholder SLAP2 field of view configuration."""
        # This is a placeholder - in production, this should be populated with actual FOV details
        return SlapFieldOfView(
            index=0,
            imaging_depth=0.0,
            targeted_structure="VISp",  # Use a valid CCF structure name
            fov_coordinate_ml=0.0,
            fov_coordinate_ap=0.0,
            fov_coordinate_dv=0.0,
            fov_reference="Unknown",
            fov_width=512,
            fov_height=512,
            fov_scale_factor=1.0,
            magnification="Unknown",
            session_type="Unknown",
            dmd_dilation_x=0,
            dmd_dilation_y=0,
            path_to_array_of_frame_rates="placeholder_path",
            notes="Placeholder SLAP2 FOV - needs actual configuration"
        )
    
    def _create_stimulus_epochs(self, session: Session) -> List[StimulusEpoch]:
        """Create stimulus epochs based on stimulus table analysis."""
        epochs = []
        
        if not self.stimulus_table_file.exists():
            logging.warning("No stimulus table found - skipping stimulus epochs")
            return epochs
        
        try:
            # Load stimulus table
            df = pd.read_csv(self.stimulus_table_file)
            
            # Analyze stimulus table to identify phases
            phases = self._identify_stimulus_phases(df)
            
            # Create epochs for each phase
            for phase_name, phase_data in phases.items():
                epoch = self._create_epoch_for_phase(session, phase_name, phase_data)
                if epoch:
                    epochs.append(epoch)
            
            logging.info(f"Created {len(epochs)} stimulus epochs: {list(phases.keys())}")
            
        except Exception as e:
            logging.error(f"Failed to create stimulus epochs: {e}")
        
        return epochs
    
    def _identify_stimulus_phases(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        Identify different stimulus phases in the data.
        
        Expected phases:
        1. Orientation Tuning (first): orientation changes constantly
        2. Oddball: orientation mostly constant 
        3. Orientation Tuning (second): orientation changes constantly again
        4. Receptive Field: x/y position changes a lot
        """
        phases = {}
        
        # Calculate orientation and position variability in sliding windows
        window_size = 100  # stimulus presentations
        orientation_std = df['orientation_degrees'].rolling(window=window_size, center=True).std()
        position_std = (df['x_position'].rolling(window=window_size, center=True).std() + 
                       df['y_position'].rolling(window=window_size, center=True).std())
        
        # Fill NaN values
        orientation_std = orientation_std.fillna(orientation_std.mean())
        position_std = position_std.fillna(position_std.mean())
        
        # Define thresholds for phase identification
        high_orientation_thresh = orientation_std.quantile(0.7)  # High variability in orientation
        low_orientation_thresh = orientation_std.quantile(0.3)   # Low variability in orientation
        high_position_thresh = position_std.quantile(0.8)        # High variability in position
        
        # Initialize phase tracking
        current_phase = None
        phase_starts = []
        phase_names = []
        
        for i, (ori_std, pos_std) in enumerate(zip(orientation_std, position_std)):
            # Determine current stimulus type
            if pos_std > high_position_thresh:
                phase_type = "receptive_field"
            elif ori_std < low_orientation_thresh:
                phase_type = "oddball"
            elif ori_std > high_orientation_thresh:
                phase_type = "orientation_tuning"
            else:
                continue  # Skip ambiguous regions
            
            # Check for phase transitions
            if current_phase != phase_type:
                if current_phase is not None:
                    # End previous phase
                    phases[phase_names[-1]]['end_idx'] = i - 1
                
                # Start new phase
                current_phase = phase_type
                phase_count = sum(1 for name in phase_names if phase_type in name)
                if phase_type == "orientation_tuning" and phase_count > 0:
                    phase_name = f"{phase_type}_{phase_count + 1}"
                else:
                    phase_name = phase_type
                
                phases[phase_name] = {
                    'start_idx': i,
                    'phase_type': phase_type
                }
                phase_starts.append(i)
                phase_names.append(phase_name)
        
        # End the last phase
        if phase_names:
            phases[phase_names[-1]]['end_idx'] = len(df) - 1
        
        # Add timing information
        for phase_name, phase_data in phases.items():
            start_idx = phase_data['start_idx']
            end_idx = phase_data['end_idx']
            
            phase_data.update({
                'start_time': df.iloc[start_idx]['start_time'],
                'end_time': df.iloc[end_idx]['stop_time'],
                'duration': df.iloc[end_idx]['stop_time'] - df.iloc[start_idx]['start_time'],
                'n_stimuli': end_idx - start_idx + 1
            })
        
        return phases
    
    def _create_epoch_for_phase(self, session: Session, phase_name: str, phase_data: Dict[str, Any]) -> Optional[StimulusEpoch]:
        """Create a StimulusEpoch for a specific stimulus phase."""
        try:
            # Calculate absolute times
            start_offset = phase_data['start_time']  # seconds from session start
            end_offset = phase_data['end_time']      # seconds from session start
            
            epoch_start_time = session.session_start_time.replace(microsecond=0) + pd.Timedelta(seconds=start_offset)
            epoch_end_time = session.session_start_time.replace(microsecond=0) + pd.Timedelta(seconds=end_offset)
            
            # Load experiment metadata for software info
            software_info = []
            if self.end_state_file.exists():
                try:
                    with open(self.end_state_file, 'r') as f:
                        end_state = json.load(f)
                    
                    script_path = end_state.get('script_path', 'Unknown')
                    script_version = end_state.get('script_version', 'Unknown')
                    
                    software_info.append(Software(
                        name=f"Predictive Processing Stimulus: {Path(script_path).name}",
                        version=script_version,
                        url=script_path
                    ))
                except Exception as e:
                    logging.warning(f"Could not load software info: {e}")
              # Create the stimulus epoch
            epoch = StimulusEpoch(
                stimulus_start_time=epoch_start_time,
                stimulus_end_time=epoch_end_time,
                stimulus_name=phase_name.replace('_', ' ').title(),
                software=software_info,
                stimulus_modalities=["Visual"],  # Use proper enum value
                stimulus_device_names=["Monitor"],
                output_parameters={
                    "phase_type": phase_data['phase_type'],
                    "duration_seconds": phase_data['duration'],
                    "n_stimuli": phase_data['n_stimuli'],
                    "description": self._get_phase_description(phase_data['phase_type'])
                }
            )
            
            return epoch
            
        except Exception as e:
            logging.error(f"Failed to create epoch for {phase_name}: {e}")
            return None
    
    def _get_phase_description(self, phase_type: str) -> str:
        """Get description for stimulus phase type."""
        descriptions = {
            "orientation_tuning": "Drifting gratings with varying orientations for orientation tuning",
            "oddball": "Oddball paradigm with mostly constant orientation and occasional deviants",
            "receptive_field": "Stimuli with varying spatial positions for receptive field mapping"
        }
        return descriptions.get(phase_type, f"Unknown stimulus phase: {phase_type}")


def enhance_existing_session(session_folder: str) -> bool:
    """
    Enhance an existing session.json with Predictive Processing-specific information.
    
    Args:
        session_folder: Path to session folder containing experiment data
        
    Returns:
        True if enhancement successful, False otherwise
    """
    enhancer = PredictiveProcessingSessionEnhancer(session_folder)
    return enhancer.enhance_session()


def run_postprocessing(param_file: str = None, overrides: dict = None) -> int:
    """
    Main entry point for Predictive Processing session enhancement post-processing.
    Loads parameters, prompts for missing fields, and runs enhancement.
    Returns 0 on success, nonzero on error.
    """
    import logging
    from pathlib import Path
    from openscope_experimental_launcher.utils import param_utils
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    required_fields = ["output_session_folder"]
    defaults = {}
    help_texts = {"output_session_folder": "Session output folder (from launcher)"}
    params = param_utils.load_parameters(
        param_file=param_file,
        overrides=overrides,
        required_fields=required_fields,
        defaults=defaults,
        help_texts=help_texts
    )
    session_folder = params["output_session_folder"]
    if not Path(session_folder).exists():
        logging.error(f"Session folder does not exist: {session_folder}")
        return 1
    enhancer = PredictiveProcessingSessionEnhancer(session_folder)
    if not enhancer.enhance_session():
        logging.error("Failed to enhance session with Predictive Processing information")
        return 1
    logging.info("Predictive Processing session enhancement completed successfully")
    return 0

if __name__ == "__main__":
    import argparse
    import sys
    parser = argparse.ArgumentParser(
        description="Enhance existing session.json files with Predictive Processing-specific information",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python session_enhancer_predictive_processing.py processed_parameters.json
        """
    )
    parser.add_argument("param_file", help="Path to processed_parameters.json from the launcher")
    args = parser.parse_args()
    sys.exit(run_postprocessing(param_file=args.param_file))
