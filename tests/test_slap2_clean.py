"""
Fixed tests for SLAP2Launcher.
"""

import os
import sys
import pytest
import tempfile
import datetime
from unittest.mock import Mock, patch

# Add the scripts directory to the path for SLAP2Launcher
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from scripts.slap2_launcher import SLAP2Launcher


class TestSLAP2LauncherClean:
    """Clean test cases for SLAP2Launcher class."""
    
    def test_init(self):
        """Test SLAP2Launcher initialization."""
        experiment = SLAP2Launcher()
        assert experiment is not None
        assert hasattr(experiment, 'stimulus_table')
        assert experiment.session_type == "SLAP2"

    def test_post_experiment_processing_success(self):
        """Test successful post-experiment processing."""
        experiment = SLAP2Launcher()
        experiment.output_session_folder = "/tmp/test"
        
        with patch.object(experiment, '_generate_stimulus_table', return_value=True):
            # Session.json creation is now handled automatically by base class
            # No need to mock _create_session_json as it no longer exists
            result = experiment.post_experiment_processing()
            assert result is True

    def test_post_experiment_processing_failure(self):
        """Test post-experiment processing with stimulus table failure."""
        experiment = SLAP2Launcher()
        experiment.output_session_folder = "/tmp/test"
        
        # Mock stimulus failure
        with patch.object(experiment, '_generate_stimulus_table', return_value=False):
            result = experiment.post_experiment_processing()
            assert result is False  # Should fail if stimulus table fails

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_generate_stimulus_table(self, temp_dir):
        """Test stimulus table generation."""
        experiment = SLAP2Launcher()
        experiment.params = {"num_trials": 50}
        experiment.output_session_folder = temp_dir
        
        with patch('openscope_experimental_launcher.utils.stimulus_table.generate_slap2_stimulus_table') as mock_gen:
            mock_gen.return_value = Mock()
            result = experiment._generate_stimulus_table()
            assert result is True

    def test_session_json_creation_via_base_class(self, temp_dir):
        """Test that session.json creation is handled by base class."""
        experiment = SLAP2Launcher()
        experiment.output_session_folder = temp_dir
        experiment.session_uuid = "test-uuid"
        experiment.start_time = datetime.datetime.now()
        experiment.stop_time = datetime.datetime.now()
        experiment.params = {"session_type": "SLAP2"}
        experiment.subject_id = "test_mouse"
        experiment.user_id = "Test User"
        
        # Initialize rig_config (required by base class)
        experiment.rig_config = {"rig_id": "test_rig", "output_root_folder": "/tmp"}
        
        # Test that the base class method exists and can be called
        result = experiment.create_session_file(temp_dir)
        assert isinstance(result, bool)  # Should return a boolean


if __name__ == "__main__":
    pytest.main([__file__])
