#!/usr/bin/env python3
"""
Bonsai Session Enhancement Post-Acquisition Tool

This tool enhances existing session.json files by adding Bonsai-specific data streams.
It loads the base session.json created by the standard SessionCreator and adds
Bonsai workflow and script streams using the AIND Session schema.

This design avoids inheritance complexity and creates clear separation between
base session creation and Bonsai-specific enhancements.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

try:
    from aind_data_schema.core.session import Session, Stream
    from aind_data_schema.components.devices import Software
    from aind_data_schema_models.modalities import Modality as StreamModality
    AIND_AVAILABLE = True
except ImportError:
    AIND_AVAILABLE = False

class BonsaiSessionEnhancer:
    """Enhance existing session.json files with Bonsai-specific information."""
    def __init__(self, output_folder: str):
        self.output_folder = Path(output_folder)
        self.session_file = self.output_folder / "session.json"
        self.end_state_file = self.output_folder / "launcher_metadata" / "end_state.json"
        self.launcher_metadata_file = self.output_folder / "launcher_metadata" / "processed_parameters.json"

    def enhance_session(self) -> bool:
        if not AIND_AVAILABLE:
            logging.error("aind-data-schema not available, cannot enhance session")
            return False
        if not self.session_file.exists():
            logging.error(f"No session.json found at {self.session_file}")
            return False
        try:
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)
            session = Session.model_validate(session_data)
            bonsai_streams = self._create_bonsai_streams(session)
            if bonsai_streams:
                session.data_streams = bonsai_streams
            if session.session_type in ['Behavior', 'Generic', 'Unknown']:
                session.session_type = 'Bonsai'
            with open(self.session_file, 'w') as f:
                json.dump(session.model_dump(), f, indent=2, default=str)
            logging.info(f"Enhanced session with {len(bonsai_streams)} Bonsai streams")
            return True
        except Exception as e:
            logging.error(f"Failed to enhance session: {e}")
            return False

    def _create_bonsai_streams(self, session: Session) -> List[Stream]:
        streams = []
        try:
            stream = self._create_script_stream(session)
            if stream:
                streams.append(stream)
        except Exception as e:
            logging.warning(f"Failed to create Bonsai stream: {e}")
        return streams

    def _create_script_stream(self, session: Session) -> Optional[Stream]:
        script_path = None
        script_parameters = {}
        if self.end_state_file.exists():
            try:
                with open(self.end_state_file, 'r') as f:
                    end_state = json.load(f)
                script_path = end_state.get('script_path')
                script_parameters = end_state.get('script_parameters', {})
            except Exception:
                pass
        if not script_path and self.launcher_metadata_file.exists():
            try:
                with open(self.launcher_metadata_file, 'r') as f:
                    launcher_metadata = json.load(f)
                script_path = launcher_metadata.get('params', {}).get('script_path')
                script_parameters = launcher_metadata.get('params', {}).get('script_parameters', {})
            except Exception:
                pass
        if not script_path:
            return None
        script_name = Path(script_path).name
        return Stream(
            stream_start_time=session.session_start_time,
            stream_end_time=session.session_end_time,
            stream_modalities=[StreamModality.BEHAVIOR],
            software=[Software(
                name=f"Bonsai Script: {script_name}",
                version="Unknown",
                url=script_path,
                parameters=script_parameters
            )]
        )

def enhance_existing_session(session_folder: str) -> bool:
    """
    Enhance an existing session.json with Bonsai-specific information.
    Args:
        session_folder: Path to session folder containing experiment data
    Returns:
        True if enhancement successful, False otherwise
    """
    enhancer = BonsaiSessionEnhancer(session_folder)
    return enhancer.enhance_session()

def run_post_acquisition(param_file: str = None, overrides: dict = None) -> int:
    """
    Main entry point for Bonsai session enhancement post-acquisition.
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
    if not enhance_existing_session(session_folder):
        logging.error("Failed to enhance session with Bonsai data")
        return 1
    logging.info("Session enhanced with Bonsai data successfully")
    return 0
