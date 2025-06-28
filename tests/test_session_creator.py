#!/usr/bin/env python3
"""
Test the session creator post-acquisition tool.
"""

import json
import os
import tempfile
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

# Skip if aind-data-schema is not available
try:
    from aind_data_schema.core.session import Session
    AIND_AVAILABLE = True
except ImportError:
    AIND_AVAILABLE = False

from openscope_experimental_launcher.post_acquisition.session_creator import SessionCreator


class TestSessionCreator:
    """Test session creator functionality."""
    
    def create_test_files(self, tmp_path):
        """Create test end_state.json and launcher_metadata.json files."""
        # Use the new nested structure that matches base_launcher.py
        end_state = {
            "launcher_info": {
                "class_name": "TestLauncher",
                "module": "test_module",
                "version": "1.0.0"
            },
            "session_info": {
                "subject_id": "test_subject_123",
                "user_id": "test_user",
                "session_uuid": "test-uuid-123",
                "start_time": "2024-01-01T10:00:00",
                "stop_time": "2024-01-01T11:00:00"
            },
            "experiment_data": {
                "experiment_notes": "Test experiment notes",
                "animal_weight_prior": None,
                "animal_weight_post": None,
                "output_session_folder": str(tmp_path)
            },
            "parameters": {
                "rig_id": "test_rig_1",
                "test_param": "test_value",
                "session_type": "Test Session"
            },
            "rig_config": {
                "rig_id": "test_rig_1",
                "mouse_platform_name": "test_platform",
                "active_mouse_platform": True
            },
            "saved_at": "2024-01-01T12:00:00"
        }
        
        launcher_metadata = {
            "launcher_class": "TestLauncher",
            "launcher_version": "1.0.0",
            "start_time": "2024-01-01T10:00:00",
            "subject_id": "test_subject_123",
            "rig_id": "test_rig_1",
            "mouse_platform_name": "test_platform",
            "active_mouse_platform": True,
            "params": {
                "test_param": "test_value",
                "session_type": "Test Session"
            }        }
        
        # Create launcher_metadata directory and write test files
        launcher_metadata_dir = tmp_path / "launcher_metadata"
        launcher_metadata_dir.mkdir()
        
        end_state_file = launcher_metadata_dir / "end_state.json"
        with open(end_state_file, 'w') as f:
            json.dump(end_state, f, indent=2)
            
        metadata_file = launcher_metadata_dir / "processed_parameters.json"
        with open(metadata_file, 'w') as f:
            json.dump(launcher_metadata, f, indent=2)
    
    def test_load_experiment_data(self, tmp_path):
        """Test loading experiment data from files."""
        self.create_test_files(tmp_path)
        
        creator = SessionCreator(str(tmp_path))
        result = creator.load_experiment_data()
        assert result is True
        assert creator.end_state["session_info"]["subject_id"] == "test_subject_123"
        assert creator.launcher_metadata["launcher_class"] == "TestLauncher"
    
    def test_create_session_file(self, tmp_path):
        """Test creating session.json file."""
        self.create_test_files(tmp_path)
        
        creator = SessionCreator(str(tmp_path))
        creator.load_experiment_data()
        
        result = creator.create_session_file()
        assert result is True
        
        # Check session file was created
        session_file = tmp_path / "session.json"
        assert session_file.exists()
        
        # Load and verify session
        with open(session_file, 'r') as f:
            session_data = json.load(f)
        
        assert session_data["subject_id"] == "test_subject_123"
        assert session_data["rig_id"] == "test_rig_1"
        assert "test_user" in session_data["experimenter_full_name"]
        assert session_data["notes"] == "Test experiment notes"
    
    def test_session_file_exists_no_force(self, tmp_path):
        """Test handling when session.json already exists."""
        self.create_test_files(tmp_path)
        
        # Create existing session file
        session_file = tmp_path / "session.json"
        session_file.write_text('{"existing": "session"}')
        
        creator = SessionCreator(str(tmp_path))
        creator.load_experiment_data()
        
        # Should not overwrite without force
        result = creator.create_session_file(force=False)
        assert result is True
        
        # File should remain unchanged
        with open(session_file, 'r') as f:
            data = json.load(f)
        assert data == {"existing": "session"}
    
    def test_session_file_overwrite_with_force(self, tmp_path):
        """Test overwriting session.json with force=True."""
        self.create_test_files(tmp_path)
        
        # Create existing session file
        session_file = tmp_path / "session.json"
        session_file.write_text('{"existing": "session"}')
        
        creator = SessionCreator(str(tmp_path))
        creator.load_experiment_data()
        
        # Should overwrite with force
        result = creator.create_session_file(force=True)
        assert result is True        
        # File should be new session
        with open(session_file, 'r') as f:
            data = json.load(f)
        assert data["subject_id"] == "test_subject_123"
    
    def test_missing_files_graceful_handling(self, tmp_path):
        """Test graceful handling when files are missing."""
        # Only create end_state.json with the new nested structure
        end_state = {
            "session_info": {
                "subject_id": "test_subject",
                "start_time": "2024-01-01T10:00:00"
            }
        }
        
        # Create launcher_metadata directory and file
        launcher_metadata_dir = tmp_path / "launcher_metadata"
        launcher_metadata_dir.mkdir()
        
        end_state_file = launcher_metadata_dir / "end_state.json"
        with open(end_state_file, 'w') as f:
            json.dump(end_state, f)
        
        creator = SessionCreator(str(tmp_path))
        result = creator.load_experiment_data()        
        # Should still succeed with partial data
        assert result is True
        assert creator.end_state["session_info"]["subject_id"] == "test_subject"
        assert creator.launcher_metadata == {}  # Empty but handled gracefully


if __name__ == "__main__":
    pytest.main([__file__])
