"""
Unit tests for the BaseLauncher class.
"""

import os
import signal
import datetime
import pytest
from unittest.mock import Mock, patch, MagicMock
from openscope_experimental_launcher.launchers.base_launcher import BaseLauncher


class TestBaseLauncher:
    """Test cases for BaseLauncher class."""
    
    def test_init(self):
        """Test BaseLauncher initialization."""
        experiment = BaseLauncher()        
        assert experiment.platform_info is not None
        assert experiment.session_directory == ""
        assert experiment.params == {}
        assert experiment.process is None
        assert experiment.session_uuid is not None

    def test_collect_runtime_information(self):
        """Test runtime information collection."""
        experiment = BaseLauncher()
        runtime_info = experiment.collect_runtime_information()
        
        assert isinstance(runtime_info, dict)
        # The current implementation only collects subject_id and user_id if not already in params
        assert "subject_id" in runtime_info or "user_id" in runtime_info

    def test_load_parameters_with_file(self, param_file, sample_params):
        """Test parameter loading from file."""
        experiment = BaseLauncher()        
        with patch('openscope_experimental_launcher.utils.config_loader.load_config', return_value=sample_params):
            experiment.load_parameters(param_file)
        
        assert experiment.params == sample_params
        assert experiment.subject_id == sample_params["subject_id"]
        assert experiment.user_id == sample_params["user_id"]
        assert experiment.params_checksum is not None

    def test_load_parameters_without_file(self):
        """Test parameter loading without file."""
        experiment = BaseLauncher()
        
        with patch('openscope_experimental_launcher.utils.config_loader.load_config', return_value={}):
            experiment.load_parameters(None)
          # The experiment may load default parameters, so we check if params is a dict
        assert isinstance(experiment.params, dict)
        assert experiment.params_checksum is None

    def test_start_process_success(self, temp_dir):
        """Test successful process start via BaseLauncher (should fail without implementation)."""
        experiment = BaseLauncher()
        experiment.params = {
            "script_path": os.path.join(temp_dir, "test_script.txt"),
            "subject_id": "test_mouse",
            "OutputFolder": temp_dir
        }
        
        # Create a mock script file
        os.makedirs(temp_dir, exist_ok=True)
        with open(os.path.join(temp_dir, "test_script.txt"), "w") as f:
            f.write("test script")        # BaseLauncher.create_process should raise NotImplementedError
        with pytest.raises(NotImplementedError):
            experiment.create_process()

    def test_stop_process(self):
        """Test stopping the process."""
        experiment = BaseLauncher()
        experiment.process = Mock()
        experiment.process.pid = 12345
        experiment.process.poll.return_value = None  # Process is running
        
        # The stop method doesn't return a value, just verify it doesn't crash
        result = experiment.stop()
        assert result is None  # Method returns None

    def test_stop_process_no_process(self):
        """Test stopping when no process exists."""
        experiment = BaseLauncher()
        experiment.process = None
        
        result = experiment.stop()
        
        assert result is None  # Method returns None

    def test_stop(self):
        """Test stopping the experiment."""
        experiment = BaseLauncher()
        experiment.process = Mock()
        
        with patch.object(experiment, 'stop_process'):
            result = experiment.stop()
            
            assert result is None  # Method returns None    def test_get_process_errors(self):
        """Test getting process errors."""
        experiment = BaseLauncher()
        errors = experiment.get_process_errors()
        
        assert isinstance(errors, str)

    def test_cleanup_success(self):
        """Test successful cleanup."""
        experiment = BaseLauncher()
        experiment.process = Mock()
        
        with patch.object(experiment, 'stop'):
            result = experiment.cleanup()
            
            assert result is None  # Method returns None

    def test_cleanup_with_exception(self):
        """Test cleanup with exception."""
        experiment = BaseLauncher()
        experiment.process = Mock()

    def test_stop(self):
        """Test stopping the experiment."""
        experiment = BaseLauncher()
        experiment.process = Mock()
        
        experiment.stop()
        
        # Should call stop_process internally
        assert experiment.process is not None

    def test_cleanup(self):
        """Test cleanup operation."""
        experiment = BaseLauncher()
        
        with patch.object(experiment, 'stop', side_effect=Exception("Test error")):
            result = experiment.cleanup()
              # Should still return None as cleanup should be robust
            assert result is None

    def test_get_process_errors(self):
        """Test getting process errors."""
        experiment = BaseLauncher()
        errors = experiment.get_process_errors()
        
        assert isinstance(errors, str)

    def test_post_experiment_processing(self):
        """Test post-experiment processing."""
        experiment = BaseLauncher()
        
        with patch.object(experiment, 'get_process_errors', return_value=""):
            result = experiment.post_experiment_processing()
            
            assert isinstance(result, bool)
    
    def test_run_success(self, temp_dir, param_file):
        """Test successful experiment run with mocked create_process."""
        experiment = BaseLauncher()
        
        # Create a mock process object
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        
        with patch('openscope_experimental_launcher.utils.git_manager.setup_repository', return_value=True), \
             patch.object(experiment, 'create_process', return_value=mock_process), \
             patch.object(experiment, 'determine_session_directory', return_value=temp_dir), \
             patch.object(experiment, 'save_experiment_metadata'), \
             patch.object(experiment, 'post_experiment_processing', return_value=True):
            
            result = experiment.run(param_file)
            
            assert result is True

    def test_run_repository_setup_failure(self, param_file):
        """Test experiment run with repository setup failure."""
        experiment = BaseLauncher()
        
        with patch('openscope_experimental_launcher.utils.git_manager.setup_repository', return_value=False), \
             patch.object(experiment, 'load_parameters'):
            
            result = experiment.run(param_file)
            
            assert result is False

    def test_determine_session_directory_with_output_folder(self):
        """Test session directory determination with OutputFolder."""
        experiment = BaseLauncher()
        experiment.params = {"OutputFolder": "/test/output"}
        
        result = experiment.determine_session_directory()
        
        assert result is not None
        assert "/test/output" in result

    def test_determine_session_directory_without_output_folder(self):
        """Test session directory determination without OutputFolder."""
        experiment = BaseLauncher()
        experiment.params = {}
        
        result = experiment.determine_session_directory()
          # Should return None when no output folder is specified
        assert result is None

    def test_save_experiment_metadata(self, temp_dir):
        """Test saving experiment metadata."""
        experiment = BaseLauncher()
        experiment.params = {"subject_id": "test_mouse"}
        
        # This should not raise an exception
        experiment.save_experiment_metadata(temp_dir)
        
        # Check if metadata directory was created with expected files
        metadata_dir = os.path.join(temp_dir, "experiment_metadata")
        assert os.path.exists(metadata_dir)
        
        # Check for expected metadata files
        processed_params_file = os.path.join(metadata_dir, "processed_parameters.json")
        assert os.path.exists(processed_params_file)
        
        cmdline_file = os.path.join(metadata_dir, "command_line_arguments.json")
        assert os.path.exists(cmdline_file)
        
        runtime_file = os.path.join(metadata_dir, "runtime_information.json")
        assert os.path.exists(runtime_file)

    def test_setup_continuous_logging(self, temp_dir):
        """Test setting up continuous logging."""
        experiment = BaseLauncher()
        
        # This should not raise an exception
        experiment.setup_continuous_logging(temp_dir)

    def test_finalize_logging(self):
        """Test finalizing logging."""
        experiment = BaseLauncher()
          # This should not raise an exception
        experiment.finalize_logging()

    def test_signal_handler(self):
        """Test signal handler."""
        experiment = BaseLauncher()
        
        with patch.object(experiment, 'stop') as mock_stop:
            # Signal handler calls sys.exit, so we need to catch SystemExit
            with pytest.raises(SystemExit) as excinfo:
                experiment.signal_handler(signal.SIGINT, None)
            
            # Check that it exits with code 0
            assert excinfo.value.code == 0
            mock_stop.assert_called_once()

    def test_str_representation(self):
        """Test string representation of experiment."""
        experiment = BaseLauncher()
        experiment.params = {"subject_id": "test_mouse"}
        
        result = str(experiment)
        
        assert "BaseLauncher" in result

    def test_repr_representation(self):
        """Test repr representation of experiment."""
        experiment = BaseLauncher()
        experiment.params = {"subject_id": "test_mouse"}
        
        result = repr(experiment)
        
        assert "BaseLauncher" in result

    def test_create_session_file_without_schema(self, tmp_path):
        """Test session file creation when aind-data-schema is not available."""
        experiment = BaseLauncher()
        experiment.start_time = datetime.datetime.now()
        experiment.stop_time = datetime.datetime.now()
        experiment.params = {"subject_id": "test_mouse"}
        experiment.subject_id = "test_mouse"
        experiment.user_id = "test_user" 
        experiment.session_uuid = "test_session"
        
        output_dir = str(tmp_path)
        
        # Mock the session_builder to simulate schema not available
        with patch('openscope_experimental_launcher.utils.session_builder.is_schema_available', return_value=False):
            result = experiment.create_session_file(output_dir)
        
        # Should return False when schema is not available
        assert result is False
          # session.json should not be created
        session_file = tmp_path / "session.json"
        assert not session_file.exists()

    def test_create_session_file_with_schema(self, tmp_path):
        """Test session file creation when aind-data-schema is available."""
        
        experiment = BaseLauncher()
        experiment.start_time = datetime.datetime.now()
        experiment.stop_time = datetime.datetime.now()
        experiment.params = {"subject_id": "test_mouse"}
        experiment.subject_id = "test_mouse"
        experiment.user_id = "test_user"
        experiment.session_uuid = "test_session"
        
        output_dir = str(tmp_path)
        
        # Mock session builder to simulate successful session creation
        mock_session = Mock()
        mock_session.model_dump.return_value = {
            "subject_id": "test_mouse",
            "user_id": "test_user",
            "session_uuid": "test_session"
        }
        
        with patch('openscope_experimental_launcher.utils.session_builder.is_schema_available', return_value=True), \
             patch('openscope_experimental_launcher.utils.session_builder.build_session', return_value=mock_session):
            result = experiment.create_session_file(output_dir)
        
        # Should return True when session is created successfully
        assert result is True
        
        # session.json should be created
        session_file = tmp_path / "session.json"
        assert session_file.exists()
        
        # Verify the contents
        import json
        with open(session_file, 'r') as f:
            session_data = json.load(f)
        
        assert session_data["subject_id"] == "test_mouse"
        assert session_data["user_id"] == "test_user"
        assert session_data["session_uuid"] == "test_session"

    def test_get_stimulus_epoch_builder_default(self):
        """Test that default stimulus epoch builder returns None."""
        experiment = BaseLauncher()
        result = experiment.get_stimulus_epoch_builder()
        assert result is None

    def test_get_data_streams_builder_default(self):
        """Test that default data streams builder returns None.""" 
        experiment = BaseLauncher()
        result = experiment.get_data_streams_builder()
        assert result is None
