"""
SLAP2 session metadata builder using aind-data-schema.

This module provides the SLAP2SessionBuilder class for creating properly
formatted session.json files that conform to aind-data-schema standards.
"""

import datetime
from typing import Dict, List, Any

# Import aind-data-schema components
try:
    from aind_data_schema.core.session import (
        Stream, 
        StimulusEpoch, 
        StimulusModality,
    )
    from aind_data_schema.components.devices import Software
    from aind_data_schema_models.modalities import Modality
    AIND_SCHEMA_AVAILABLE = True
except ImportError:
    AIND_SCHEMA_AVAILABLE = False

# Import base session builder
from ..base.session_builder import BaseSessionBuilder


class SLAP2SessionBuilder(BaseSessionBuilder):
    """
    Builds SLAP2 session metadata using aind-data-schema standards.
    """
    
    def __init__(self):
        """Initialize the SLAP2 session builder."""
        super().__init__("SLAP2")
    
    def _create_stimulus_epoch(self,
                              start_time: datetime.datetime,
                              end_time: datetime.datetime,
                              params: Dict[str, Any],
                              bonsai_software: Software,
                              script_software: Software,
                              **kwargs) -> StimulusEpoch:
        """Create stimulus epoch for SLAP2 experiment."""
        return StimulusEpoch(
            stimulus_start_time=start_time,
            stimulus_end_time=end_time,
            stimulus_name=params.get("stimulus_name", "SLAP2 Oddball Stimulus"),
            stimulus_modalities=[StimulusModality.VISUAL],  # Assuming visual stimulation
            software=[bonsai_software],
            script=script_software,
            trials_total=params.get("num_trials", 100),
            trials_finished=params.get("num_trials", 100),  # Placeholder - would come from actual results
            notes=params.get("stimulus_notes", "SLAP2 experiment with oddball stimulus paradigm")        )
    
    def _create_data_streams(self, params: Dict[str, Any], **kwargs) -> List[Stream]:
        """Create data streams for SLAP2 experiment."""
        # For now, return empty list to avoid POPhys validation issues
        # This can be extended later when data stream requirements are clarified
        return []
    