#!/usr/bin/env python3
"""
Session Creation Post-Acquisition Tool

This tool creates session.json files from experiment data by reading
the output folder contents. This design allows session files to be
regenerated after the fact from the experiment data.

The tool reads:
- end_state.json: Runtime information saved at experiment end
- launcher_metadata.json: Launcher configuration and parameters
- Experiment output files: To determine data streams and timing

Usage:
    python session_creator.py <output_folder>
    python session_creator.py <output_folder> --force  # Overwrite existing session.json
"""

import json
import logging
from pathlib import Path
from openscope_experimental_launcher.utils import param_utils
from datetime import datetime
from typing import Dict, Any, List, Optional

try:
    from aind_data_schema.core.session import Session, Stream
    from aind_data_schema.components.devices import Software
    from aind_data_schema_models.modalities import Modality as StreamModality
    AIND_DATA_SCHEMA_AVAILABLE = True
except ImportError:
    AIND_DATA_SCHEMA_AVAILABLE = False
    logging.warning("aind-data-schema not available, session creation will be skipped")

class SessionCreator:
    """Create session.json files from experiment output folders."""
    def __init__(self, output_folder: str):
        self.output_folder = Path(output_folder)
        self.end_state_file = self.output_folder / "launcher_metadata" / "end_state.json"
        self.launcher_metadata_file = self.output_folder / "launcher_metadata" / "processed_parameters.json"
        self.session_file = self.output_folder / "session.json"
        self.end_state = {}
        self.launcher_metadata = {}

    def load_experiment_data(self) -> bool:
        try:
            if self.end_state_file.exists():
                with open(self.end_state_file, 'r') as f:
                    self.end_state = json.load(f)
                logging.info(f"Loaded end state with {len(self.end_state)} entries")
            else:
                logging.warning(f"No end_state.json found at {self.end_state_file}")
            if self.launcher_metadata_file.exists():
                with open(self.launcher_metadata_file, 'r') as f:
                    self.launcher_metadata = json.load(f)
                logging.info("Loaded launcher metadata")
            else:
                logging.warning(f"No launcher_metadata.json found at {self.launcher_metadata_file}")
            return True
        except Exception as e:
            logging.error(f"Failed to load experiment data: {e}")
            return False

    def create_session_file(self, force: bool = False) -> bool:
        if not AIND_DATA_SCHEMA_AVAILABLE:
            logging.error("aind-data-schema not available, cannot create session file")
            return False
        if self.session_file.exists() and not force:
            logging.info(f"Session file already exists: {self.session_file}")
            logging.info("Use --force to overwrite")
            return True
        try:
            session_start_time = self._get_session_start_time()
            session_end_time = self._get_session_end_time()
            session_info = self.end_state.get('session_info', {})
            subject_id = session_info.get('subject_id', self.launcher_metadata.get('subject_id', 'unknown'))
            session = Session(
                experimenter_full_name=[session_info.get('user_id', 'unknown')],
                session_start_time=session_start_time,
                session_end_time=session_end_time,
                subject_id=subject_id,
                session_type=self._get_session_type(),
                rig_id=self.end_state.get('parameters', {}).get('rig_id', self.launcher_metadata.get('rig_id', 'unknown')),
                notes=self._get_session_notes(),
                data_streams=self._get_data_streams(session_start_time, session_end_time),
                mouse_platform_name=self.launcher_metadata.get('mouse_platform_name', 'unknown'),
                active_mouse_platform=self.launcher_metadata.get('active_mouse_platform', False)
            )
            with open(self.session_file, 'w') as f:
                f.write(session.model_dump_json(indent=2))
            logging.info(f"Session file created: {self.session_file}")
            return True
        except Exception as e:
            logging.error(f"Failed to create session file: {e}")
            return False

    def _get_session_start_time(self) -> datetime:
        session_info = self.end_state.get('session_info', {})
        start_time_str = session_info.get('start_time')
        if start_time_str:
            try:
                return datetime.fromisoformat(start_time_str)
            except ValueError:
                pass
        logging.warning("Could not determine session start time, using current time")
        return datetime.now()

    def _get_session_end_time(self) -> datetime:
        session_info = self.end_state.get('session_info', {})
        end_time_str = session_info.get('stop_time')
        if end_time_str:
            try:
                return datetime.fromisoformat(end_time_str)
            except ValueError:
                pass
        return self._get_session_start_time()

    def _get_session_type(self) -> str:
        return 'Behavior'

    def _get_session_notes(self) -> Optional[str]:
        experiment_data = self.end_state.get('experiment_data', {})
        notes = experiment_data.get('experiment_notes')
        return notes if notes else None

    def _get_data_streams(self, start_time: datetime, end_time: Optional[datetime]) -> List:
        if not AIND_DATA_SCHEMA_AVAILABLE:
            return []
        streams = []
        try:
            launcher_info = self.end_state.get('launcher_info', {})
            launcher_name = launcher_info.get('class_name', 'Unknown')
            if launcher_name != 'Unknown':
                launcher_name = f"{launcher_name} Launcher"
            parameters = self.end_state.get('parameters', {})
            launcher_stream = Stream(
                stream_start_time=start_time,
                stream_end_time=end_time,
                stream_modalities=[StreamModality.BEHAVIOR],
                software=[Software(
                    name=launcher_name,
                    version=launcher_info.get('version', 'unknown'),
                    url="https://github.com/AllenInstitute/openscope-experimental-launcher",
                    parameters=parameters
                )]
            )
            streams.append(launcher_stream)
        except Exception as e:
            logging.warning(f"Failed to create launcher stream: {e}")
        return streams

def run_post_acquisition(param_file: str = None, overrides: dict = None) -> int:
    """
    Main entry point for session creation post-acquisition.
    Loads parameters, prompts for missing fields, and runs session creation.
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
    creator = SessionCreator(session_folder)
    if not creator.load_experiment_data():
        logging.error("Failed to load experiment data")
        return 1
    force = False
    if overrides and "force" in overrides:
        force = overrides["force"]
    if not creator.create_session_file(force=force):
        logging.error("Failed to create session.json file")
        return 1
    logging.info("Session file created successfully")
    return 0
