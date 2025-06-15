"""
SLAP2 session metadata builder using aind-data-schema.

This module provides the SLAP2SessionBuilder class for creating properly
formatted session.json files that conform to aind-data-schema standards.
"""

import logging
import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal

# Import aind-data-schema components
try:
    from aind_data_schema.core.session import (
        Session, 
        Stream, 
        StimulusEpoch, 
        StimulusModality,
        SlapFieldOfView,
        LaserConfig,
        DetectorConfig
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
            notes=params.get("stimulus_notes", "SLAP2 experiment with oddball stimulus paradigm")
        )
    
    def _create_data_streams(self, params: Dict[str, Any], **kwargs) -> List[Stream]:
        """Create data streams for SLAP2 experiment."""
        # For now, return empty list to avoid POPhys validation issues
        # This can be extended later when data stream requirements are clarified        return []
    
    # Removed unnecessary _get_additional_script_parameters override - base class returns {} by default
    
    def _create_light_sources(self, params: Dict[str, Any]) -> List[LaserConfig]:
        """Create light source configurations for SLAP2."""
        light_sources = []
        
        if params.get("laser_wavelength") and params.get("laser_power"):
            laser_config = self._create_laser_config(
                name=params.get("laser_name", "SLAP2 Laser"),
                wavelength=params.get("laser_wavelength", 920),
                power=params.get("laser_power", 10.0)
            )
            light_sources.append(laser_config)
        
        return light_sources
    
    def _create_detectors(self, params: Dict[str, Any]) -> List[DetectorConfig]:
        """Create detector configurations for SLAP2."""
        detectors = []
        
        if params.get("detector_name"):
            detector_config = self._create_detector_config(
                name=params.get("detector_name", "SLAP2 Detector"),
                exposure_time=params.get("exposure_time", 1.0),
                trigger_type=params.get("trigger_type", "External")
            )
            detectors.append(detector_config)
        
        return detectors
    
    def build_session(self,
                     start_time: Optional[datetime.datetime] = None,
                     end_time: Optional[datetime.datetime] = None,
                     params: Optional[Dict[str, Any]] = None,
                     mouse_id: str = "",
                     user_id: str = "",
                     experimenter_name: str = "",
                     session_uuid: str = "",
                     slap_fovs: Optional[List[SlapFieldOfView]] = None,
                     **kwargs) -> Optional[Session]:
        """
        Build a complete Session object for SLAP2 experiments.
        
        Maintains backward compatibility with the original SLAP2 interface
        while leveraging the base class functionality.
        
        Args:
            start_time: Session start time
            end_time: Session end time
            params: Experiment parameters
            mouse_id: Subject ID
            user_id: User ID
            experimenter_name: Experimenter's full name
            session_uuid: Unique session identifier
            slap_fovs: List of SLAP field of view objects (SLAP2-specific)
            **kwargs: Additional parameters
            
        Returns:
            Session object or None if building failed
        """
        # Pass slap_fovs as a kwarg to the base class
        if slap_fovs is not None:
            kwargs['slap_fovs'] = slap_fovs
        
        return super().build_session(
            start_time=start_time,
            end_time=end_time,
            params=params,
            mouse_id=mouse_id,
            user_id=user_id,
            experimenter_name=experimenter_name,
            session_uuid=session_uuid,
            **kwargs
        )