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


# Adjusted tests for flattened end_state and crash_info without exception_message
class TestEndStateDebugState:
    def test_save_end_state(self, tmp_path):
        """Test saving end state information."""
        # Create a minimal launcher
        launcher = BaseLauncher()
        launcher.subject_id = "test_subject"
        launcher.user_id = "test_user"
        launcher.session_uuid = "test_uuid"
        launcher.rig_config = {"rig_id": "test_rig"}
        launcher.experiment_notes = "Test experiment"
        result = launcher.save_end_state(str(tmp_path))
        assert result is True
        end_state_file = tmp_path / "launcher_metadata" / "end_state.json"
        with open(end_state_file) as f:
            end_state = json.load(f)
        assert end_state["subject_id"] == "test_subject"
        assert end_state["user_id"] == "test_user"
        assert end_state["session_uuid"] == "test_uuid"
        assert end_state["rig_config"]["rig_id"] == "test_rig"

    def test_save_debug_state(self, tmp_path):
        """Test saving debug state for crash analysis."""
        # Create a launcher with some state
        launcher = BaseLauncher()
        launcher.subject_id = "debug_subject"
        test_exception = ValueError("Test error for debugging")
        launcher.save_debug_state(str(tmp_path), test_exception)
        debug_state_file = tmp_path / "launcher_metadata" / "debug_state.json"
        with open(debug_state_file) as f:
            debug_state = json.load(f)
        assert debug_state["crash_info"]["exception_type"] == "ValueError"
        assert debug_state["crash_info"]["message"] == "Test error for debugging"
        assert "crash_time" in debug_state["crash_info"]

    def test_debug_state_on_crash(self, tmp_path):
        """Test that debug state is saved when run() crashes."""
        
        class CrashingLauncher(BaseLauncher):
            def start_experiment(self):
                raise RuntimeError("Simulated crash")
        
        # Create launcher and set up minimal state
        launcher = CrashingLauncher()
        launcher.output_session_folder = str(tmp_path)
        launcher.rig_config = {"rig_id": "crash_rig"}
        launcher.subject_id = "crash_subject"
        with patch('openscope_experimental_launcher.launchers.base_launcher.git_manager.setup_repository', return_value=True), \
             patch.object(launcher, 'determine_output_session_folder', return_value=str(tmp_path)), \
             patch.object(launcher, 'setup_continuous_logging'), \
             patch.object(launcher, 'save_launcher_metadata'), \
             patch.object(launcher, 'stop'):
            result = launcher.run()
        assert result is False
        debug_state_file = tmp_path / "launcher_metadata" / "debug_state.json"
        with open(debug_state_file) as f:
            debug_state = json.load(f)
        assert debug_state["crash_info"]["exception_type"] == "RuntimeError"
        assert debug_state["crash_info"]["message"] == "Simulated crash"


if __name__ == "__main__":
    pytest.main([__file__])
