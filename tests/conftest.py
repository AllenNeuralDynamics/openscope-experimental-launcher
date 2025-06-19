"""
Test configuration and utilities for openscope-experimental-launcher.

This module provides common test fixtures, utilities, and configuration
for the test suite.
"""

import os
import tempfile
import shutil
import json
from typing import Dict, Any
import pytest
from unittest.mock import Mock, patch


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_params():
    """Sample experiment parameters for testing."""
    return {
        "subject_id": "test_mouse_123",
        "user_id": "Test User",
        "session_type": "SLAP2",
        "rig_id": "test_rig",
        "num_trials": 50,
        "laser_power": 15.0,
        "laser_wavelength": 920,
        "frame_rate": 30.0,
        "bonsai_path": "workflows/test_workflow.bonsai",
        "repository_url": "https://github.com/test/repo.git",
        "repository_commit_hash": "main",
        "local_repository_path": "/tmp/test_repo"
    }


@pytest.fixture
def sample_slap_fovs():
    """Sample SLAP field of view parameters."""
    return [
        {
            "index": 0,
            "imaging_depth": 150,
            "targeted_structure": "VISp",
            "fov_coordinate_ml": 2.5,
            "fov_coordinate_ap": -2.0,
            "fov_reference": "Bregma",
            "fov_width": 512,
            "fov_height": 512,
            "magnification": "40x",
            "fov_scale_factor": 1.0,
            "frame_rate": 30.0,
            "session_type": "Parent",
            "dmd_dilation_x": 3,
            "dmd_dilation_y": 3
        }
    ]


@pytest.fixture
def sample_config():
    """Sample CamStim configuration."""
    return {
        "Behavior": {
            "subject_id": "test_mouse",
            "user_id": "test_user",
            "nidevice": "Dev1"
        },
        "Stim": {
            "fps": 60.0,
            "monitor_brightness": 30
        }
    }


@pytest.fixture
def mock_subprocess():
    """Mock subprocess calls for testing."""
    with patch('subprocess.Popen') as mock_popen, \
         patch('subprocess.check_call') as mock_check_call, \
         patch('subprocess.check_output') as mock_check_output:
        
        # Configure mock process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.returncode = 0
        mock_process.poll.return_value = 0
        mock_process.stdout.readline.return_value = ""
        mock_process.stderr.readline.return_value = ""
        mock_process.stdout.read.return_value = ""
        mock_process.stderr.read.return_value = ""
        
        mock_popen.return_value = mock_process
        mock_check_output.return_value = b"test output"
        
        yield {
            'popen': mock_popen,
            'check_call': mock_check_call,
            'check_output': mock_check_output,
            'process': mock_process
        }


@pytest.fixture
def mock_git_available():
    """Mock Git availability check."""
    with patch('subprocess.check_output') as mock_check_output:
        mock_check_output.return_value = b"git version 2.34.1"
        yield mock_check_output


@pytest.fixture
def param_file(temp_dir, sample_params):
    """Create a temporary parameter file."""
    param_path = os.path.join(temp_dir, "test_params.json")
    with open(param_path, 'w') as f:
        json.dump(sample_params, f)
    return param_path


class MockDateTime:
    """Mock datetime for consistent testing."""
    
    @classmethod
    def now(cls):
        from datetime import datetime
        return datetime(2025, 6, 12, 10, 30, 0)


@pytest.fixture
def mock_datetime():
    """Mock datetime.datetime.now() for consistent testing."""
    with patch('datetime.datetime') as mock_dt:
        mock_dt.now.return_value = MockDateTime.now()
        mock_dt.side_effect = lambda *args, **kwargs: MockDateTime.now() if not args else None
        yield mock_dt
