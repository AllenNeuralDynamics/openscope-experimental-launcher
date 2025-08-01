"""
Tests for BonsaiLauncher class focusing on the new modular architecture.
"""

import os
import pytest
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock, mock_open

from openscope_experimental_launcher.launchers.bonsai_launcher import BonsaiLauncher


class TestBonsaiLauncher:
    """Test cases for BonsaiLauncher class."""

    def test_init(self):
        """Test BonsaiLauncher initialization."""
        launcher = BonsaiLauncher()
        assert launcher is not None
        assert hasattr(launcher, 'platform_info')
        assert hasattr(launcher, 'session_uuid')
        assert hasattr(launcher, 'process')

    def test_create_process_success(self, temp_dir):
        """Test successful process creation."""
        launcher = BonsaiLauncher()
        launcher.params = {
            "script_path": os.path.join(temp_dir, "test_workflow.bonsai"),            "bonsai_exe_path": os.path.join(temp_dir, "Bonsai.exe"),
            "subject_id": "test_mouse",
            "output_root_folder": temp_dir
        }
          # Create mock files
        os.makedirs(temp_dir, exist_ok=True)
        with open(os.path.join(temp_dir, "test_workflow.bonsai"), "w") as f:
            f.write("<WorkflowBuilder>Test</WorkflowBuilder>")
        with open(os.path.join(temp_dir, "Bonsai.exe"), "w") as f:
            f.write("mock exe")
        
        with patch('openscope_experimental_launcher.interfaces.bonsai_interface.start_workflow') as mock_start:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_start.return_value = mock_process
            
            with patch('openscope_experimental_launcher.interfaces.bonsai_interface.setup_bonsai_environment', return_value=True):
                result = launcher.create_process()
                
                assert result == mock_process
                assert launcher.process == mock_process

    def test_create_process_failure(self, temp_dir):
        """Test process creation failure."""
        launcher = BonsaiLauncher()
        launcher.params = {
            "script_path": os.path.join(temp_dir, "nonexistent.bonsai"),            "bonsai_exe_path": os.path.join(temp_dir, "Bonsai.exe"),
            "subject_id": "test_mouse",
            "output_root_folder": temp_dir
        }
          # Don't create the workflow file - should fail
        
        try:
            result = launcher.create_process()
            # If we get here, the test should fail since it should have raised an exception
            assert False, "Expected RuntimeError to be raised"
        except RuntimeError:
            # This is expected
            assert launcher.process is None
    
    def test_get_process_errors(self):
        """Test getting process errors."""
        launcher = BonsaiLauncher()
        launcher.stderr_data = ["Error 1", "Error 2"]
        
        errors = launcher.get_process_errors()
        
        assert isinstance(errors, str)
        assert "Error 1" in errors
        assert "Error 2" in errors
    
    def test_get_process_errors_no_errors(self):
        """Test getting process errors when none exist."""
        launcher = BonsaiLauncher()
        launcher.stderr_data = []
        
        errors = launcher.get_process_errors()
        
        assert errors == "No errors reported by Bonsai."

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir
