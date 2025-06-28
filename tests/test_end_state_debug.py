#!/usr/bin/env python3
"""
Test the end state and debug state functionality of BaseLauncher.
"""

import json
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from openscope_experimental_launcher.launchers.base_launcher import BaseLauncher


class TestEndStateDebugState:
    """Test end state and debug state functionality."""
    
    def test_save_end_state(self, tmp_path):
        """Test saving end state information."""
        # Create a minimal launcher
        launcher = BaseLauncher()
        launcher.subject_id = "test_subject"
        launcher.user_id = "test_user"
        launcher.session_uuid = "test_uuid"
        launcher.rig_config = {"rig_id": "test_rig"}
        launcher.experiment_notes = "Test experiment"
        launcher.start_time = launcher.stop_time = None  # Will be handled gracefully
        
        # Save end state
        result = launcher.save_end_state(str(tmp_path))
        assert result is True
        
        # Check end state file was created in launcher_metadata directory
        end_state_file = tmp_path / "launcher_metadata" / "end_state.json"
        assert end_state_file.exists()
        
        # Load and verify end state
        with open(end_state_file, 'r') as f:
            end_state = json.load(f)
        
        assert end_state["session_info"]["subject_id"] == "test_subject"
        assert end_state["session_info"]["user_id"] == "test_user"
        assert end_state["session_info"]["session_uuid"] == "test_uuid"
        assert end_state["rig_config"]["rig_id"] == "test_rig"
        # experiment_notes may not be present if handled by a post-acquisition module
        if "experiment_notes" in end_state.get("experiment_data", {}):
            assert end_state["experiment_data"]["experiment_notes"] == "Test experiment"

    def test_save_debug_state(self, tmp_path):
        """Test saving debug state for crash analysis."""
        # Create a launcher with some state
        launcher = BaseLauncher()
        launcher.subject_id = "debug_subject"
        launcher.test_attribute = "debug_value"
        
        # Create a test exception
        test_exception = ValueError("Test error for debugging")
          # Save debug state
        result = launcher.save_debug_state(str(tmp_path), test_exception)
        assert result is True
          # Check debug state file was created in launcher_metadata directory
        debug_state_file = tmp_path / "launcher_metadata" / "debug_state.json"
        assert debug_state_file.exists()
        
        # Load and verify debug state
        with open(debug_state_file, 'r') as f:
            debug_state = json.load(f)
        
        assert debug_state["crash_info"]["exception_type"] == "ValueError"
        assert debug_state["crash_info"]["exception_message"] == "Test error for debugging"
        assert "crash_time" in debug_state["crash_info"]
        assert "launcher_state" in debug_state
        assert debug_state["launcher_state"]["subject_id"] == "debug_subject"
        assert debug_state["launcher_state"]["test_attribute"] == "debug_value"

    def test_custom_end_state_data(self, tmp_path):
        """Test that subclasses can add custom end state data."""
        
        class CustomLauncher(BaseLauncher):
            def __init__(self):
                super().__init__()
                self.custom_value = "custom_data"
                
            def get_custom_end_state(self):
                return {
                    "custom_field": self.custom_value,
                    "launcher_specific_info": "important_data"
                }
        
        # Create custom launcher
        launcher = CustomLauncher()
        launcher.subject_id = "custom_subject"
        launcher.rig_config = {"rig_id": "custom_rig"}
        
        # Save end state
        result = launcher.save_end_state(str(tmp_path))
        assert result is True        # Load and verify custom data was included
        end_state_file = tmp_path / "launcher_metadata" / "end_state.json"
        with open(end_state_file, 'r') as f:
            end_state = json.load(f)
        
        assert end_state["custom_data"]["custom_field"] == "custom_data"
        assert end_state["custom_data"]["launcher_specific_info"] == "important_data"
        assert end_state["session_info"]["subject_id"] == "custom_subject"
    
    def test_debug_state_on_crash(self, tmp_path):
        """Test that debug state is saved when run() crashes."""
        
        class CrashingLauncher(BaseLauncher):
            def __init__(self):
                super().__init__()
                self.crash_attribute = "will_be_saved"
                
            def start_experiment(self):
                raise RuntimeError("Simulated crash")
        
        # Create launcher and set up minimal state
        launcher = CrashingLauncher()
        launcher.output_session_folder = str(tmp_path)
        launcher.rig_config = {"rig_id": "crash_rig"}
        launcher.subject_id = "crash_subject"
        
        # Mock the repository setup to avoid git operations
        with patch('openscope_experimental_launcher.launchers.base_launcher.git_manager.setup_repository', return_value=True):
            with patch.object(launcher, 'determine_output_session_folder', return_value=str(tmp_path)):
                with patch.object(launcher, 'setup_continuous_logging'):
                    with patch.object(launcher, 'save_launcher_metadata'):
                        with patch.object(launcher, 'stop'):
                            # Run should fail but save debug state
                            result = launcher.run()
                
        assert result is False
          # Check debug state was saved in launcher_metadata directory
        debug_state_file = tmp_path / "launcher_metadata" / "debug_state.json"
        assert debug_state_file.exists()
          # Verify debug info
        with open(debug_state_file, 'r') as f:
            debug_state = json.load(f)
        
        assert debug_state["crash_info"]["exception_type"] == "RuntimeError"
        assert debug_state["crash_info"]["exception_message"] == "Simulated crash"
        assert debug_state["launcher_state"]["crash_attribute"] == "will_be_saved"


if __name__ == "__main__":
    pytest.main([__file__])
