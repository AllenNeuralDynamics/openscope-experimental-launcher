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


class SLAP2SessionBuilder:
    """
    Builds SLAP2 session metadata using aind-data-schema standards.
    """
    
    def __init__(self):
        """Initialize the SLAP2 session builder."""
        if not AIND_SCHEMA_AVAILABLE:
            logging.warning("aind-data-schema not available. Session building will be disabled.")
    
    def build_session(self,
                     start_time: Optional[datetime.datetime],
                     end_time: Optional[datetime.datetime],
                     params: Dict[str, Any],
                     mouse_id: str,
                     user_id: str,
                     experimenter_name: str,
                     session_uuid: str,
                     slap_fovs: List[SlapFieldOfView]) -> Optional[Session]:
        """
        Build a complete Session object for SLAP2 experiments.
        
        Args:
            start_time: Session start time
            end_time: Session end time
            params: Experiment parameters
            mouse_id: Subject ID
            user_id: User ID
            experimenter_name: Experimenter's full name
            session_uuid: Unique session identifier
            slap_fovs: List of SLAP field of view objects
            
        Returns:
            Session object or None if building failed
        """
        if not AIND_SCHEMA_AVAILABLE:
            logging.error("Cannot build session: aind-data-schema not available")
            return None
        
        try:
            # Set default times if not provided
            if not start_time:
                start_time = datetime.datetime.now()
            if not end_time:
                end_time = datetime.datetime.now()
            
            # Create software information for Bonsai
            bonsai_software = self._create_bonsai_software(params)
            
            # Create script information
            script_software = self._create_script_software(params, mouse_id, user_id, session_uuid)
            
            # Create stimulus epoch
            stimulus_epoch = self._create_stimulus_epoch(
                start_time, end_time, params, bonsai_software, script_software
            )
            
            # Create the session with stimulus information only (no data streams for now)
            session = Session(
                experimenter_full_name=[experimenter_name],
                session_start_time=start_time,
                session_end_time=end_time,
                session_type=params.get("session_type", "SLAP2"),
                rig_id=params.get("rig_id", "slap2_rig"),
                subject_id=mouse_id,
                mouse_platform_name=params.get("mouse_platform", "Fixed platform"),
                active_mouse_platform=params.get("active_mouse_platform", False),
                data_streams=[],  # Empty data streams to avoid POPhys validation issues
                stimulus_epochs=[stimulus_epoch],
                notes=f"SLAP2 experiment session for {mouse_id} by {user_id} - stimulus information only"
            )
            
            logging.info("SLAP2 session object created successfully (stimulus-only)")
            return session
            
        except Exception as e:
            logging.error(f"Failed to build SLAP2 session: {e}")
            return None
    
    def _create_bonsai_software(self, params: Dict[str, Any]) -> Software:
        """Create Software object for Bonsai."""
        return Software(
            name="Bonsai",
            version=params.get("bonsai_version", "Unknown"),
            url="https://bonsai-rx.org/",
            parameters=params
        )
    
    def _create_script_software(self, 
                               params: Dict[str, Any], 
                               mouse_id: str, 
                               user_id: str, 
                               session_uuid: str) -> Software:
        """Create Software object for the stimulus script."""
        return Software(
            name="SLAP2 Stimulus Script",
            version="1.0.0",
            url=params.get("repository_url", ""),
            parameters={
                "workflow_path": params.get("bonsai_path", ""),
                "mouse_id": mouse_id,
                "user_id": user_id,
                "session_uuid": session_uuid
            }
        )
    
    def _create_light_sources(self, params: Dict[str, Any]) -> List[LaserConfig]:
        """Create light source configurations for SLAP2."""
        light_sources = []
        
        if params.get("laser_wavelength") and params.get("laser_power"):
            laser_config = LaserConfig(
                name=params.get("laser_name", "SLAP2 Laser"),
                wavelength=int(params.get("laser_wavelength", 920)),
                excitation_power=Decimal(str(params.get("laser_power", 10.0)))
            )
            light_sources.append(laser_config)
        
        return light_sources
    
    def _create_detectors(self, params: Dict[str, Any]) -> List[DetectorConfig]:
        """Create detector configurations for SLAP2."""
        detectors = []
        
        if params.get("detector_name"):
            detector_config = DetectorConfig(
                name=params.get("detector_name", "SLAP2 Detector"),
                exposure_time=Decimal(str(params.get("exposure_time", 1.0))),
                trigger_type=params.get("trigger_type", "External")
            )
            detectors.append(detector_config)
        
        return detectors
    
    def _create_stimulus_epoch(self,
                              start_time: datetime.datetime,
                              end_time: datetime.datetime,
                              params: Dict[str, Any],
                              bonsai_software: Software,
                              script_software: Software) -> StimulusEpoch:
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