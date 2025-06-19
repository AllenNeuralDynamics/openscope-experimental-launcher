"""
Session metadata builder functions using aind-data-schema.

This module provides functions for creating properly formatted session.json files 
that conform to aind-data-schema standards. It replaces the class-based approach
with a more functional design.
"""

import logging
import datetime
from typing import Dict, List, Optional, Any, Union, Callable
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
    logging.warning("aind-data-schema not available. Session building will be disabled.")


def is_schema_available() -> bool:
    """Check if aind-data-schema is available."""
    return AIND_SCHEMA_AVAILABLE


def build_session(
    start_time: Optional[datetime.datetime] = None,
    end_time: Optional[datetime.datetime] = None,
    params: Optional[Dict[str, Any]] = None,
    subject_id: str = "",
    user_id: str = "",
    session_uuid: str = "",
    rig_name: str = "Generic",
    stimulus_epoch_builder: Optional[Callable] = None,
    data_streams_builder: Optional[Callable] = None,
    **kwargs
) -> Optional[Session]:
    """
    Build a complete Session object for experiments.
    
    Args:
        start_time: Session start time
        end_time: Session end time
        params: Experiment parameters
        subject_id: Subject ID
        user_id: User ID
        session_uuid: Unique session identifier
        rig_name: Name of the rig (e.g., "SLAP2", "Neuropixels")
        stimulus_epoch_builder: Function to create stimulus epoch
        data_streams_builder: Function to create data streams
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
        bonsai_software = create_bonsai_software(params)
        
        # Create script information
        script_software = create_script_software(params, subject_id, user_id, session_uuid, rig_name)
        
        # Create stimulus epoch
        if stimulus_epoch_builder:
            stimulus_epoch = stimulus_epoch_builder(
                start_time, end_time, params, bonsai_software, script_software, **kwargs
            )
        else:
            stimulus_epoch = create_default_stimulus_epoch(
                start_time, end_time, params, bonsai_software, script_software, rig_name
            )
        
        # Create data streams
        if data_streams_builder:
            data_streams = data_streams_builder(params, **kwargs)
        else:
            data_streams = create_default_data_streams(params, rig_name)
        
        # Ensure data_streams is always a list
        if data_streams is None:
            data_streams = []
        
        # Create the session
        session = Session(
            experimenter_full_name=[user_id] if user_id else [],
            session_start_time=start_time,
            session_end_time=end_time,
            session_type=get_session_type(params, rig_name),
            rig_id=get_rig_id(params, rig_name),
            subject_id=subject_id,
            mouse_platform_name=get_mouse_platform_name(params),
            active_mouse_platform=get_active_mouse_platform(params),
            data_streams=data_streams,
            stimulus_epochs=[stimulus_epoch],
            notes=create_session_notes(params, subject_id, user_id, rig_name)
        )
        
        logging.info(f"{rig_name} session object created successfully")
        return session
        
    except Exception as e:
        logging.error(f"Failed to build {rig_name} session: {e}")
        return None


def create_bonsai_software(params: Dict[str, Any]) -> Software:
    """Create Software object for Bonsai."""
    return Software(
        name="Bonsai",
        version=params.get("bonsai_version", "Unknown"),
        url="https://bonsai-rx.org/",
        parameters=params
    )


def create_script_software(
    params: Dict[str, Any], 
    subject_id: str, 
    user_id: str, 
    session_uuid: str,
    rig_name: str = "Generic"
) -> Software:
    """Create Software object for the stimulus script."""
    return Software(
        name=get_script_name(rig_name),
        version=params.get("script_version", "1.0.0"),
        url=params.get("repository_url", ""),
        parameters={
            "workflow_path": params.get("bonsai_path", ""),
            "subject_id": subject_id,
            "user_id": user_id,
            "session_uuid": session_uuid,
            **get_additional_script_parameters(params, rig_name)
        }
    )


def create_default_stimulus_epoch(
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    params: Dict[str, Any],
    bonsai_software: Software,
    script_software: Software,
    rig_name: str = "Generic"
) -> StimulusEpoch:
    """Create a default stimulus epoch."""
    return StimulusEpoch(
        stimulus_start_time=start_time,
        stimulus_end_time=end_time,
        stimulus_name=f"{rig_name} Stimulus",
        software=[bonsai_software, script_software],
        stimulus_modalities=[StimulusModality.VISUAL],  # Default to visual
        stimulus_parameters=params.get("stimulus_parameters", {})
    )


def create_default_data_streams(params: Dict[str, Any], rig_name: str = "Generic") -> List[Stream]:
    """Create default data streams."""
    # Return empty list for default implementation
    # Rig-specific implementations should override this
    return []


def get_session_type(params: Dict[str, Any], rig_name: str = "Generic") -> str:
    """Get the session type for this rig."""
    return params.get("session_type", rig_name)


def get_rig_id(params: Dict[str, Any], rig_name: str = "Generic") -> str:
    """Get the rig ID for this rig."""
    default_rig_id = f"{rig_name.lower()}_rig"
    return params.get("rig_id", default_rig_id)


def get_mouse_platform_name(params: Dict[str, Any]) -> str:
    """Get the mouse platform name."""
    return params.get("mouse_platform", "Fixed platform")


def get_active_mouse_platform(params: Dict[str, Any]) -> bool:
    """Get whether the mouse platform is active."""
    return params.get("active_mouse_platform", False)


def get_script_name(rig_name: str = "Generic") -> str:
    """Get the name of the stimulus script."""
    return f"{rig_name} Stimulus Script"


def get_additional_script_parameters(params: Dict[str, Any], rig_name: str = "Generic") -> Dict[str, Any]:
    """Get additional rig-specific script parameters."""
    return {}


def create_session_notes(params: Dict[str, Any], subject_id: str, user_id: str, rig_name: str = "Generic") -> str:
    """Create session notes."""
    base_notes = f"{rig_name} experiment session for {subject_id}"
    if user_id:
        base_notes += f" by {user_id}"
    
    additional_notes = params.get("session_notes", "")
    if additional_notes:
        base_notes += f" - {additional_notes}"
    
    return base_notes


# SLAP2-specific functions
def create_slap2_stimulus_epoch(
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    params: Dict[str, Any],
    bonsai_software: Software,
    script_software: Software,
    **kwargs
) -> StimulusEpoch:
    """Create SLAP2-specific stimulus epoch."""
    # Extract SLAP2-specific parameters
    slap_fovs = params.get("slap_fovs", [])
    field_of_view_configs = []
    
    for fov in slap_fovs:
        if isinstance(fov, dict):
            field_of_view_configs.append(
                SlapFieldOfView(
                    index=fov.get("index", 0),
                    imaging_depth=fov.get("imaging_depth", 0),
                    targeted_structure=fov.get("targeted_structure", "Unknown"),
                    fov_coordinate_ml=fov.get("fov_coordinate_ml", 0.0),
                    fov_coordinate_ap=fov.get("fov_coordinate_ap", 0.0)
                )
            )
    
    # Create laser configuration
    laser_config = LaserConfig(
        wavelength=params.get("laser_wavelength", 920),
        power=params.get("laser_power", 0.0)
    )
    
    return StimulusEpoch(
        stimulus_start_time=start_time,
        stimulus_end_time=end_time,
        stimulus_name="SLAP2 Visual Stimulus",
        software=[bonsai_software, script_software],
        stimulus_modalities=[StimulusModality.VISUAL],
        stimulus_parameters={
            "num_trials": params.get("num_trials", 0),
            "frame_rate": params.get("frame_rate", 30.0),
            "field_of_view_configs": field_of_view_configs,
            "laser_config": laser_config,
            **params.get("stimulus_parameters", {})
        }
    )


def create_slap2_data_streams(params: Dict[str, Any], **kwargs) -> List[Stream]:
    """Create SLAP2-specific data streams."""
    streams = []
    
    # Add imaging stream
    imaging_stream = Stream(
        stream_start_time=datetime.datetime.now(),
        stream_end_time=datetime.datetime.now(),
        daq_names=["SLAP2_Imaging"],
        stream_modalities=[Modality.SLAP]
    )
    streams.append(imaging_stream)
    
    # Add behavior stream if behavior data is expected
    if params.get("collect_behavior", True):
        behavior_stream = Stream(
            stream_start_time=datetime.datetime.now(),
            stream_end_time=datetime.datetime.now(),
            daq_names=["Behavior"],
            stream_modalities=[Modality.BEHAVIOR]
        )
        streams.append(behavior_stream)
    
    return streams


def build_slap2_session(
    start_time: Optional[datetime.datetime] = None,
    end_time: Optional[datetime.datetime] = None,
    params: Optional[Dict[str, Any]] = None,
    subject_id: str = "",
    user_id: str = "",
    session_uuid: str = "",
    **kwargs
) -> Optional[Session]:
    """
    Build a SLAP2-specific session object.
    
    This is a convenience function that uses SLAP2-specific builders.
    """
    return build_session(
        start_time=start_time,
        end_time=end_time,
        params=params,
        subject_id=subject_id,
        user_id=user_id,
        session_uuid=session_uuid,
        rig_name="SLAP2",
        stimulus_epoch_builder=create_slap2_stimulus_epoch,
        data_streams_builder=create_slap2_data_streams,
        **kwargs
    )
