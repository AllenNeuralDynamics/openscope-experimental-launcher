"""
Example rig session metadata builder using aind-data-schema.

This module demonstrates how to create a rig-specific session builder
by extending the BaseSessionBuilder class.
"""

import logging
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
from ..base.session_builder import BaseSessionBuilder


class ExampleRigSessionBuilder(BaseSessionBuilder):
    """
    Example session builder for a generic rig.
    
    This demonstrates how to extend BaseSessionBuilder for different rig types.
    """
    
    def __init__(self):
        """Initialize the example rig session builder."""
        super().__init__("ExampleRig")
    
    def _create_stimulus_epoch(self,
                              start_time: datetime.datetime,
                              end_time: datetime.datetime,
                              params: Dict[str, Any],
                              bonsai_software: Software,
                              script_software: Software,
                              **kwargs) -> StimulusEpoch:
        """Create stimulus epoch for example rig experiment."""
        # Determine stimulus modalities based on parameters
        modalities = []
        if params.get("visual_stimulus", True):
            modalities.append(StimulusModality.VISUAL)
        if params.get("auditory_stimulus", False):
            modalities.append(StimulusModality.AUDITORY)
        if not modalities:  # Default to visual if nothing specified
            modalities = [StimulusModality.VISUAL]
        
        return StimulusEpoch(
            stimulus_start_time=start_time,
            stimulus_end_time=end_time,
            stimulus_name=params.get("stimulus_name", "Generic Stimulus"),
            stimulus_modalities=modalities,
            software=[bonsai_software],
            script=script_software,
            trials_total=params.get("num_trials", 50),
            trials_finished=params.get("trials_completed", params.get("num_trials", 50)),
            notes=params.get("stimulus_notes", "Generic experiment with customizable stimulus paradigm")
        )
    
    def _create_data_streams(self, params: Dict[str, Any], **kwargs) -> List[Stream]:
        """Create data streams for example rig experiment."""
        # This is where you would define the specific data streams for your rig
        # For example: behavior camera, neural recording, eye tracking, etc.
        
        # For now, return empty list
        # In a real implementation, you would create Stream objects here
        return []
    
    def _get_additional_script_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get additional example rig-specific script parameters."""
        return {
            "rig_specific_param": params.get("custom_parameter", "default_value"),
            "experiment_type": params.get("experiment_type", "generic")
        }
    
    def _get_session_type(self, params: Dict[str, Any]) -> str:
        """Get the session type for this rig."""
        # You can customize the session type based on parameters
        experiment_type = params.get("experiment_type", "generic")
        return f"ExampleRig_{experiment_type}"
    
    def _get_mouse_platform_name(self, params: Dict[str, Any]) -> str:
        """Get the mouse platform name for this rig."""
        return params.get("mouse_platform", "Running wheel")
    
    def _get_active_mouse_platform(self, params: Dict[str, Any]) -> bool:
        """Get whether the mouse platform is active for this rig."""
        return params.get("active_mouse_platform", True)  # Default to active for example rig
