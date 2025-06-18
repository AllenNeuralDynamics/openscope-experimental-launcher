"""
Base session metadata builder using aind-data-schema.

This module provides the BaseSessionBuilder class for creating properly
formatted session.json files that conform to aind-data-schema standards.
It can be extended by rig-specific implementations.
"""

import logging
import datetime
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
from abc import ABC, abstractmethod

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


class BaseSessionBuilder(ABC):
    """
    Base class for building session metadata using aind-data-schema standards.
    
    This class provides common functionality for session building that can be
    extended by rig-specific implementations (e.g., SLAP2, Neuropixels, etc.).
    """
    
    def __init__(self, rig_name: str):
        """
        Initialize the base session builder.
        
        Args:
            rig_name: Name of the rig (e.g., "SLAP2", "Neuropixels")
        """
        self.rig_name = rig_name
        if not AIND_SCHEMA_AVAILABLE:
            logging.warning("aind-data-schema not available. Session building will be disabled.")
    
    def build_session(self,
                     start_time: Optional[datetime.datetime] = None,
                     end_time: Optional[datetime.datetime] = None,
                     params: Optional[Dict[str, Any]] = None,
                     subject_id: str = "",
                     user_id: str = "",
                     experimenter_name: str = "",
                     session_uuid: str = "",
                     **kwargs) -> Optional[Session]:
        """
        Build a complete Session object for experiments.
        
        Args:
            start_time: Session start time
            end_time: Session end time
            params: Experiment parameters
            subject_id: Subject ID
            user_id: User ID
            session_uuid: Unique session identifier
            **kwargs: Additional rig-specific parameters
            
        Returns:
            Session object or None if building failed
        """
        if not AIND_SCHEMA_AVAILABLE:
            logging.error("Cannot build session: aind-data-schema not available")
            return None
        
        if not params:
            params = {}
        
        try:
            # Set default times if not provided
            if not start_time:
                start_time = datetime.datetime.now()
            if not end_time:
                end_time = datetime.datetime.now()
            
            # Create software information for Bonsai
            bonsai_software = self._create_bonsai_software(params)
            
            # Create script information
            script_software = self._create_script_software(params, subject_id, user_id, session_uuid)
            
            # Create stimulus epoch
            stimulus_epoch = self._create_stimulus_epoch(
                start_time, end_time, params, bonsai_software, script_software, **kwargs
            )
              # Create data streams (rig-specific)
            data_streams = self._create_data_streams(params, **kwargs)
            
            # Ensure data_streams is always a list (defensive programming)
            if data_streams is None:
                data_streams = []
            
            # Create the session
            session = Session(
                experimenter_full_name=[user_id] if user_id else [],
                session_start_time=start_time,
                session_end_time=end_time,
                session_type=self._get_session_type(params),
                rig_id=self._get_rig_id(params),
                subject_id=subject_id,
                mouse_platform_name=self._get_mouse_platform_name(params),
                active_mouse_platform=self._get_active_mouse_platform(params),
                data_streams=data_streams,
                stimulus_epochs=[stimulus_epoch],
                notes=self._create_session_notes(params, subject_id, user_id)
            )
            
            logging.info(f"{self.rig_name} session object created successfully")
            return session
            
        except Exception as e:
            logging.error(f"Failed to build {self.rig_name} session: {e}")
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
                               subject_id: str, 
                               user_id: str, 
                               session_uuid: str) -> Software:
        """Create Software object for the stimulus script."""
        return Software(
            name=self._get_script_name(),
            version=params.get("script_version", "1.0.0"),
            url=params.get("repository_url", ""),
            parameters={
                "workflow_path": params.get("bonsai_path", ""),
                "subject_id": subject_id,
                "user_id": user_id,
                "session_uuid": session_uuid,
                **self._get_additional_script_parameters(params)
            }
        )
    
    @abstractmethod
    def _create_stimulus_epoch(self,
                              start_time: datetime.datetime,
                              end_time: datetime.datetime,
                              params: Dict[str, Any],
                              bonsai_software: Software,
                              script_software: Software,
                              **kwargs) -> StimulusEpoch:
        """
        Create stimulus epoch for the experiment.
        
        This method must be implemented by rig-specific subclasses.
        """
        pass
    
    @abstractmethod
    def _create_data_streams(self, params: Dict[str, Any], **kwargs) -> List[Stream]:
        """
        Create data streams for the experiment.
        
        This method must be implemented by rig-specific subclasses.
        """
        pass
    
    def _get_session_type(self, params: Dict[str, Any]) -> str:
        """Get the session type for this rig."""
        return params.get("session_type", self.rig_name)
    
    def _get_rig_id(self, params: Dict[str, Any]) -> str:
        """Get the rig ID for this rig."""
        default_rig_id = f"{self.rig_name.lower()}_rig"
        return params.get("rig_id", default_rig_id)
    
    def _get_mouse_platform_name(self, params: Dict[str, Any]) -> str:
        """Get the mouse platform name."""
        return params.get("mouse_platform", "Fixed platform")
    
    def _get_active_mouse_platform(self, params: Dict[str, Any]) -> bool:
        """Get whether the mouse platform is active."""
        return params.get("active_mouse_platform", False)
    
    def _get_script_name(self) -> str:
        """Get the name of the stimulus script."""
        return f"{self.rig_name} Stimulus Script"
    
    def _get_additional_script_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get additional rig-specific script parameters."""
        return {}
    
    def _create_session_notes(self, params: Dict[str, Any], subject_id: str, user_id: str) -> str:
        """Create session notes."""
        base_notes = f"{self.rig_name} experiment session for {subject_id}"
        if user_id:
            base_notes += f" by {user_id}"
        
        additional_notes = params.get("session_notes", "")
        if additional_notes:
            base_notes += f" - {additional_notes}"
        
        return base_notes
    
