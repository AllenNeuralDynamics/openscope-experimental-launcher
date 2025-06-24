#!/usr/bin/env python3
"""
Bonsai Session Enhancement Post-Processing Tool

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
        """
        Enhance session.json with Bonsai-specific data streams.
        
        Returns:
            True if enhancement successful, False otherwise
        """
        if not AIND_AVAILABLE:
            logging.error("aind-data-schema not available, cannot enhance session")
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
            
            # Add Bonsai-specific streams
            bonsai_streams = self._create_bonsai_streams(session)
            if bonsai_streams:
                if session.data_streams:
                    session.data_streams.extend(bonsai_streams)
                else:
                    session.data_streams = bonsai_streams
                
                # Update session type if it's generic
                if session.session_type in ['Behavior', 'Generic', 'Unknown']:
                    session.session_type = 'Bonsai'
                
                # Save enhanced session
                with open(self.session_file, 'w') as f:
                    json.dump(session.model_dump(), f, indent=2, default=str)
                
                logging.info(f"Enhanced session with {len(bonsai_streams)} Bonsai streams")
                return True
            else:
                logging.warning("No Bonsai streams created - nothing to enhance")
                return True
                
        except Exception as e:
            logging.error(f"Failed to enhance session: {e}")
            return False
    
    def _create_bonsai_streams(self, session: Session) -> List[Stream]:
        """Create Bonsai-specific data streams based on available data."""
        streams = []
        
        # Load experiment data
        end_state = {}
        launcher_metadata = {}
        
        if self.end_state_file.exists():
            with open(self.end_state_file, 'r') as f:
                end_state = json.load(f)
        
        if self.launcher_metadata_file.exists():
            with open(self.launcher_metadata_file, 'r') as f:
                launcher_metadata = json.load(f)
        
        # Create main Bonsai script stream
        script_stream = self._create_script_stream(session, end_state, launcher_metadata)
        if script_stream:
            streams.append(script_stream)
        
        # Create streams for .bonsai workflow files
        workflow_streams = self._create_workflow_streams(session)
        streams.extend(workflow_streams)
        
        return streams
    
    def _create_script_stream(self, session: Session, end_state: dict, launcher_metadata: dict) -> Optional[Stream]:
        """Create a stream for the main Bonsai script/workflow."""
        # Get script information
        script_path = (end_state.get('script_path') or 
                      launcher_metadata.get('script_path') or
                      launcher_metadata.get('params', {}).get('script_path'))
        
        if not script_path:
            return None
        
        script_name = Path(script_path).name
        script_parameters = (end_state.get('script_parameters') or 
                           launcher_metadata.get('params', {}).get('script_parameters', {}))
        
        return Stream(
            stream_start_time=session.session_start_time,
            stream_end_time=session.session_end_time,
            stream_modalities=[StreamModality.BEHAVIOR],
            software=[Software(
                name=f"Bonsai Script: {script_name}",
                version=end_state.get("script_version", "Unknown"),
                url=script_path,
                parameters=script_parameters
            )]
        )
    
    def _create_workflow_streams(self, session: Session) -> List[Stream]:
        """Create streams for .bonsai workflow files in output directory."""
        streams = []
        
        for bonsai_file in self.output_folder.glob("*.bonsai"):
            try:
                stream = Stream(
                    stream_start_time=session.session_start_time,
                    stream_end_time=session.session_end_time,
                    stream_modalities=[StreamModality.BEHAVIOR],
                    software=[Software(
                        name=f"Bonsai Workflow: {bonsai_file.name}",
                        version="unknown",
                        url=str(bonsai_file),
                        parameters={}
                    )]
                )
                streams.append(stream)
            except Exception as e:
                logging.warning(f"Failed to create stream for {bonsai_file.name}: {e}")
        
        return streams


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


def main():
    """Command-line interface."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        description="Enhance existing session.json files with Bonsai-specific information",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python session_enhancer_bonsai.py /path/to/session_folder
  python session_enhancer_bonsai.py /path/to/session_folder --verbose        """
    )
    
    parser.add_argument(
        "session_folder",
        help="Path to session folder containing experiment data and session.json"
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Check if session folder exists
    if not Path(args.session_folder).exists():
        logging.error(f"Session folder does not exist: {args.session_folder}")
        return 1
    
    # Enhance the session
    if not enhance_existing_session(args.session_folder):
        logging.error("Failed to enhance session with Bonsai information")
        return 1
    
    logging.info("Bonsai session enhancement completed successfully")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
