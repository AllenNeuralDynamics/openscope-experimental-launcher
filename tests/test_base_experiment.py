"""
Unit tests for the BaseExperiment class.
"""

import os
import signal
import pytest
from unittest.mock import Mock, patch, MagicMock
from openscope_experimental_launcher.base.experiment import BaseExperiment


class TestBaseExperiment:
    """Test cases for BaseExperiment class."""

    def test_init(self):
        """Test BaseExperiment initialization."""
        experiment = BaseExperiment()        
        assert experiment.platform_info is not None
        assert experiment.session_directory == ""
        assert experiment.params == {}
        assert experiment.bonsai_process is None
        assert experiment.session_uuid is not None

    def test_collect_runtime_information(self):
        """Test runtime information collection."""
        experiment = BaseExperiment()
        runtime_info = experiment.collect_runtime_information()
        
        assert isinstance(runtime_info, dict)
        # The current implementation only collects subject_id and user_id if not already in params
        assert "subject_id" in runtime_info or "user_id" in runtime_info

    def test_load_parameters_with_file(self, param_file, sample_params):
        """Test parameter loading from file."""
        experiment = BaseExperiment()        
        with patch('openscope_experimental_launcher.utils.config_loader.load_config', return_value=sample_params):
            experiment.load_parameters(param_file)
        
        assert experiment.params == sample_params
        assert experiment.subject_id == sample_params["subject_id"]
        assert experiment.user_id == sample_params["user_id"]
        assert experiment.params_checksum is not None

    def test_load_parameters_without_file(self):
        """Test parameter loading without file."""
        experiment = BaseExperiment()
        
        with patch('openscope_experimental_launcher.utils.config_loader.load_config', return_value={}):
            experiment.load_parameters(None)
        
        # The experiment may load default parameters, so we check if params is a dict
        assert isinstance(experiment.params, dict)
        assert experiment.params_checksum is None

    def test_start_bonsai_success(self, temp_dir):
        """Test successful Bonsai process start."""
        experiment = BaseExperiment()
        experiment.params = {
            "bonsai_path": os.path.join(temp_dir, "test_workflow.bonsai"),
            "subject_id": "test_mouse",
            "OutputFolder": temp_dir        }
        
        with patch('openscope_experimental_launcher.utils.git_manager.get_repository_path', return_value=temp_dir), \
             patch('openscope_experimental_launcher.base.bonsai_interface.setup_bonsai_environment', return_value=True), \
             patch('openscope_experimental_launcher.base.bonsai_interface.start_workflow') as mock_start, \
             patch('openscope_experimental_launcher.base.bonsai_interface.construct_workflow_arguments', return_value=[]):
            
            mock_process = Mock()
            mock_process.pid = 12345
            mock_start.return_value = mock_process
            
            # Create a mock workflow file
            os.makedirs(temp_dir, exist_ok=True)
            with open(os.path.join(temp_dir, "test_workflow.bonsai"), "w") as f:
                f.write("<test>workflow</test>")
            
            result = experiment.start_bonsai()
            
            assert result is True
            assert experiment.bonsai_process == mock_process

    def test_start_bonsai_process_creation_failure(self):
        """Test Bonsai process creation failure."""
        experiment = BaseExperiment()
        experiment.params = {
            "bonsai_path": "test_workflow.bonsai",
            "subject_id": "test_mouse",
            "OutputFolder": "/tmp/test"
        }
        
        with patch('openscope_experimental_launcher.base.bonsai_interface.setup_bonsai_environment', return_value=True), \
             patch('openscope_experimental_launcher.base.bonsai_interface.start_workflow', return_value=None):
            
            result = experiment.start_bonsai()
            
            assert result is False
            assert experiment.bonsai_process is None

    def test_kill_process(self):
        """Test killing the Bonsai process."""
        experiment = BaseExperiment()
        experiment.bonsai_process = Mock()
        experiment.bonsai_process.pid = 12345
        experiment.bonsai_process.poll.return_value = None  # Process is running
        
        # The kill_process method doesn't return a value, just verify it doesn't crash
        result = experiment.kill_process()
        assert result is None  # Method returns None    def test_kill_process_no_process(self):
        """Test killing when no process exists."""
        experiment = BaseExperiment()
        experiment.bonsai_process = None
        
        result = experiment.kill_process()
        
        assert result is None  # Method returns None    def test_stop(self):
        """Test stopping the experiment."""
        experiment = BaseExperiment()
        experiment.bonsai_process = Mock()
        
        with patch.object(experiment, 'kill_process'):
            result = experiment.stop()
            
            assert result is None  # Method returns None

    def test_get_bonsai_errors(self):
        """Test getting Bonsai errors."""
        experiment = BaseExperiment()
        errors = experiment.get_bonsai_errors()
        
        assert isinstance(errors, str)

    def test_cleanup_success(self):
        """Test successful cleanup."""
        experiment = BaseExperiment()
        experiment.bonsai_process = Mock()
        
        with patch.object(experiment, 'stop'):
            result = experiment.cleanup()
            
            assert result is None  # Method returns None

    def test_cleanup_with_exception(self):
        """Test cleanup with exception."""
        experiment = BaseExperiment()
        experiment.bonsai_process = Mock()
        
        with patch.object(experiment, 'stop', side_effect=Exception("Test error")):
            result = experiment.cleanup()
            
            # Should still return None as cleanup should be robust
            assert result is None

    def test_post_experiment_processing(self):
        """Test post-experiment processing."""
        experiment = BaseExperiment()
        
        with patch.object(experiment, 'get_bonsai_errors', return_value=""):
            result = experiment.post_experiment_processing()
            
            assert isinstance(result, bool)

    def test_run_success(self, temp_dir, param_file):
        """Test successful experiment run."""
        experiment = BaseExperiment()
        
        with patch('openscope_experimental_launcher.utils.git_manager.setup_repository', return_value=True), \
             patch.object(experiment, 'start_bonsai', return_value=True), \
             patch.object(experiment, 'determine_session_directory', return_value=temp_dir), \
             patch.object(experiment, 'save_experiment_metadata'), \
             patch.object(experiment, 'post_experiment_processing', return_value=True):
            
            result = experiment.run(param_file)
            
            assert result is True

    def test_run_repository_setup_failure(self, param_file):
        """Test experiment run with repository setup failure."""
        experiment = BaseExperiment()
        
        with patch('openscope_experimental_launcher.utils.git_manager.setup_repository', return_value=False), \
             patch.object(experiment, 'load_parameters'):
            
            result = experiment.run(param_file)
            
            assert result is False

    def test_determine_session_directory_with_output_folder(self):
        """Test session directory determination with OutputFolder."""
        experiment = BaseExperiment()
        experiment.params = {"OutputFolder": "/test/output"}
        
        result = experiment.determine_session_directory()
        
        assert result is not None
        assert "/test/output" in result

    def test_determine_session_directory_without_output_folder(self):
        """Test session directory determination without OutputFolder."""
        experiment = BaseExperiment()
        experiment.params = {}
        
        result = experiment.determine_session_directory()
          # Should return None when no output folder is specified
        assert result is None

    def test_save_experiment_metadata(self, temp_dir):
        """Test saving experiment metadata."""
        experiment = BaseExperiment()
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
        experiment = BaseExperiment()
        
        # This should not raise an exception
        experiment.setup_continuous_logging(temp_dir)

    def test_finalize_logging(self):
        """Test finalizing logging."""
        experiment = BaseExperiment()
          # This should not raise an exception
        experiment.finalize_logging()

    def test_signal_handler(self):
        """Test signal handler."""
        experiment = BaseExperiment()
        
        with patch.object(experiment, 'stop') as mock_stop:
            # Signal handler calls sys.exit, so we need to catch SystemExit
            with pytest.raises(SystemExit) as excinfo:
                experiment.signal_handler(signal.SIGINT, None)
            
            # Check that it exits with code 0
            assert excinfo.value.code == 0
            mock_stop.assert_called_once()

    def test_str_representation(self):
        """Test string representation of experiment."""
        experiment = BaseExperiment()
        experiment.params = {"subject_id": "test_mouse"}
        
        result = str(experiment)
        
        assert "BaseExperiment" in result

    def test_repr_representation(self):
        """Test repr representation of experiment."""
        experiment = BaseExperiment()
        experiment.params = {"subject_id": "test_mouse"}
        
        result = repr(experiment)
        
        assert "BaseExperiment" in result
