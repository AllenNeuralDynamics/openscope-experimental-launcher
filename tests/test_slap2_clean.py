"""
Fixed tests for SLAP2Launcher.
"""

import os
import sys
import pytest
import tempfile
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
        experiment.session_directory = "/tmp/test"
        
        with patch.object(experiment, '_generate_stimulus_table', return_value=True):
            with patch.object(experiment, '_create_session_json', return_value=True):
                with patch.object(experiment, '_process_fov_data', return_value=True):
                    result = experiment.post_experiment_processing()
                    assert result is True

    def test_post_experiment_processing_failure(self):
        """Test post-experiment processing with session failure."""
        experiment = SLAP2Launcher()
        experiment.session_directory = "/tmp/test"
        
        # Mock stimulus success but session failure
        with patch.object(experiment, '_generate_stimulus_table', return_value=True):
            with patch.object(experiment, '_create_session_json', return_value=False):
                with patch.object(experiment, '_process_fov_data', return_value=True):
                    result = experiment.post_experiment_processing()
                    assert result is False  # Should fail if session json fails

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_generate_stimulus_table(self, temp_dir):
        """Test stimulus table generation."""
        experiment = SLAP2Launcher()
        experiment.params = {"num_trials": 50}
        experiment.session_directory = temp_dir
        
        with patch('openscope_experimental_launcher.utils.stimulus_table.generate_slap2_stimulus_table') as mock_gen:
            mock_gen.return_value = Mock()
            result = experiment._generate_stimulus_table()
            assert result is True

    def test_create_session_json(self, temp_dir):
        """Test session json creation."""
        experiment = SLAP2Launcher()
        experiment.session_directory = temp_dir
        experiment.session_uuid = "test-uuid"
        experiment.start_time = Mock()
        experiment.stop_time = Mock()
        experiment.params = {"session_type": "SLAP2"}
        experiment.subject_id = "test_mouse"
        experiment.user_id = "Test User"
          # Mock the session object properly
        mock_session = Mock()
        mock_session.model_dump_json.return_value = '{"test": "session_data"}'
        
        with patch('openscope_experimental_launcher.utils.session_builder.build_session', return_value=mock_session):
            result = experiment._create_session_json()
            assert result is True


if __name__ == "__main__":
    pytest.main([__file__])
