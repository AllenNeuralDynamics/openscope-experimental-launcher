"""
Example: Creating a Neuropixels session builder using the base class.

This example demonstrates how to create a session builder for a Neuropixels rig
by extending the BaseSessionBuilder class.
"""

import datetime
from typing import Dict, List, Optional, Any

# Import aind-data-schema components
try:
    from aind_data_schema.core.session import (
        Stream, 
        StimulusEpoch, 
        StimulusModality,
    )
    from aind_data_schema.components.devices import Software
    AIND_SCHEMA_AVAILABLE = True
except ImportError:
    AIND_SCHEMA_AVAILABLE = False

# Import base session builder
from openscope_experimental_launcher.base.session_builder import BaseSessionBuilder


class NeuropixelsSessionBuilder(BaseSessionBuilder):
    """
    Session builder for Neuropixels experiments.
    
    This demonstrates how to extend BaseSessionBuilder for a different rig type.
    """
    
    def __init__(self):
        """Initialize the Neuropixels session builder."""
        super().__init__("Neuropixels")
    
    def _create_stimulus_epoch(self,
                              start_time: datetime.datetime,
                              end_time: datetime.datetime,
                              params: Dict[str, Any],
                              bonsai_software: Software,
                              script_software: Software,
                              **kwargs) -> StimulusEpoch:
        """Create stimulus epoch for Neuropixels experiment."""
        
        # Neuropixels experiments often use multiple stimulus modalities
        modalities = [StimulusModality.VISUAL]  # Default to visual
        
        # Add auditory if specified
        if params.get("include_auditory", False):
            modalities.append(StimulusModality.AUDITORY)
        
        # Add optogenetic if specified
        if params.get("include_optogenetic", False):
            modalities.append(StimulusModality.OPTOGENETIC)
        
        return StimulusEpoch(
            stimulus_start_time=start_time,
            stimulus_end_time=end_time,
            stimulus_name=params.get("stimulus_name", "Neuropixels Multi-Modal Stimulus"),
            stimulus_modalities=modalities,
            software=[bonsai_software],
            script=script_software,
            trials_total=params.get("num_trials", 200),  # Neuropixels experiments often have more trials
            trials_finished=params.get("trials_completed", params.get("num_trials", 200)),
            notes=params.get("stimulus_notes", "Neuropixels experiment with visual and optional auditory/optogenetic stimulation")
        )
    
    def _create_data_streams(self, params: Dict[str, Any], **kwargs) -> List[Stream]:
        """Create data streams for Neuropixels experiment."""
        streams = []
        
        # In a real implementation, you would create Stream objects for:
        # - Neural data from Neuropixels probes
        # - Behavioral camera data
        # - Eye tracking data
        # - Lick detection data
        # - etc.
        
        # For now, return empty list as placeholder
        return streams
    
    def _get_session_type(self, params: Dict[str, Any]) -> str:
        """Get the session type for Neuropixels experiments."""
        # You can customize based on the type of Neuropixels experiment
        experiment_type = params.get("experiment_type", "visual_behavior")
        return f"Neuropixels_{experiment_type}"
    
    def _get_rig_id(self, params: Dict[str, Any]) -> str:
        """Get the rig ID for Neuropixels experiments."""
        # Different Neuropixels rigs might have different IDs
        rig_number = params.get("rig_number", "1")
        return f"neuropixels_rig_{rig_number}"
    
    def _get_mouse_platform_name(self, params: Dict[str, Any]) -> str:
        """Get the mouse platform name for Neuropixels experiments."""
        # Neuropixels experiments often use running wheels
        return params.get("mouse_platform", "Running wheel")
    
    def _get_active_mouse_platform(self, params: Dict[str, Any]) -> bool:
        """Get whether the mouse platform is active for Neuropixels experiments."""
        # Running wheels are typically active
        return params.get("active_mouse_platform", True)
    
    def _get_additional_script_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get additional Neuropixels-specific script parameters."""
        return {
            "probe_configuration": params.get("probe_config", "default"),
            "recording_duration": params.get("recording_duration_minutes", 60),
            "probe_insertion_depth": params.get("probe_depth_um", 3000),
            "brain_regions": params.get("target_brain_regions", ["VISp", "VISl"]),
        }


# Example usage
def example_usage():
    """
    Example of how to use the NeuropixelsSessionBuilder.
    """
    builder = NeuropixelsSessionBuilder()
    
    # Example parameters for a Neuropixels experiment
    params = {
        "stimulus_name": "Drifting Gratings + Natural Movies",
        "num_trials": 300,
        "include_auditory": True,
        "include_optogenetic": False,
        "experiment_type": "visual_behavior",
        "rig_number": "2",
        "probe_config": "four_shank_linear",
        "recording_duration_minutes": 90,
        "probe_depth_um": 3500,
        "target_brain_regions": ["VISp", "VISl", "VISal", "VISpm"],
        "repository_url": "https://github.com/AllenInstitute/neuropixels_experiment",
        "bonsai_version": "2.8.0",
    }
    
    # Build the session
    session = builder.build_session(
        start_time=datetime.datetime(2024, 1, 15, 10, 0, 0),
        end_time=datetime.datetime(2024, 1, 15, 11, 30, 0),
        params=params,
        mouse_id="mouse_456789",
        user_id="neuropixels_user",
        experimenter_name="Jane Smith",
        session_uuid="neuropixels-session-uuid-123",
        # Add any Neuropixels-specific parameters
        probe_serial_numbers=["probe_001", "probe_002"],
        headstage_serial_number="headstage_123"
    )
    
    if session:
        print(f"Created session: {session.session_type}")
        print(f"Rig ID: {session.rig_id}")
        print(f"Duration: {session.session_end_time - session.session_start_time}")
        print(f"Stimulus epochs: {len(session.stimulus_epochs)}")
        print(f"Data streams: {len(session.data_streams)}")
    else:
        print("Failed to create session")


if __name__ == "__main__":
    example_usage()
