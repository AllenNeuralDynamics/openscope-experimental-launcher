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
        with patch('openscope_experimental_launcher.utils.rig_config.get_rig_config', return_value={'rig_id': 'test_rig'}):
            experiment = BaseLauncher()        
        assert experiment.platform_info is not None
        assert experiment.output_session_folder == ""
        assert 'rig_id' in experiment.params  # rig_config gets merged into params
        assert experiment.process is None
        assert experiment.session_uuid is not None

    def test_initialize_launcher_with_file(self, param_file, sample_params):
        """Test launcher initialization from file."""
        with patch('openscope_experimental_launcher.utils.rig_config.get_rig_config', return_value={'rig_id': 'test_rig', 'output_root_folder': '/tmp'}):
            experiment = BaseLauncher(param_file=param_file)
        
        # Check that all original params are present
        for key, value in sample_params.items():
            assert experiment.params[key] == value
          # Check that rig_config fields are also merged into params
        assert experiment.params["output_root_folder"] == "/tmp"
        
        assert experiment.subject_id == sample_params["subject_id"]
        assert experiment.user_id == sample_params["user_id"]

    def test_initialize_launcher_without_file(self):
        """Test launcher initialization without file."""
        with patch('openscope_experimental_launcher.utils.rig_config.get_rig_config', return_value={'rig_id': 'test_rig', 'output_root_folder': '/tmp'}):
            experiment = BaseLauncher(param_file=None)
        
        # The experiment may load default parameters, so we check if params is a dict
        assert isinstance(experiment.params, dict)

    def test_start_process_success(self, temp_dir):
        """Test successful process start via BaseLauncher (dummy subprocess)."""
        experiment = BaseLauncher()
        experiment.params = {
            "script_path": os.path.join(temp_dir, "test_script.txt"),
            "subject_id": "test_mouse",
            "output_root_folder": temp_dir
        }
        # Create a mock script file
        os.makedirs(temp_dir, exist_ok=True)
        with open(os.path.join(temp_dir, "test_script.txt"), "w") as f:
            f.write("test script")
        # BaseLauncher.create_process should run a dummy subprocess and return a process object
        process = experiment.create_process()
        assert process is not None
        assert hasattr(process, 'poll')

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
            
            assert result is None  # Method returns None
            
    def test_get_process_errors(self):
        """Test getting process errors."""
        experiment = BaseLauncher()
        errors = experiment.get_process_errors()
        
        assert isinstance(errors, list)

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
        
        assert isinstance(errors, list)

    def test_post_experiment_acquisition(self):
        """Test post-experiment post-acquisition functionality."""
        experiment = BaseLauncher()
        experiment.param_file = "/tmp/test_session"
        # Prepare a fake processed_parameters.json content
        fake_json = '{"output_session_folder": "/tmp/test_session"}'
        from unittest.mock import mock_open
        m = mock_open(read_data=fake_json)
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', m):
            result = experiment.run_post_acquisition(param_file="/tmp/test_session")
            assert isinstance(result, bool)

    def test_run_success(self, temp_dir, param_file):
        """Test successful experiment run with mocked create_process."""
        # Initialize with the parameter file
        with patch('openscope_experimental_launcher.utils.rig_config.get_rig_config', return_value={'rig_id': 'test_rig', 'output_root_folder': temp_dir}):
            experiment = BaseLauncher(param_file=param_file)
        
        # Create a mock process object
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        
        def mock_start_experiment():
            experiment.process = mock_process  # Set the process attribute
            return True
        
        with patch('openscope_experimental_launcher.utils.git_manager.setup_repository', return_value=True), \
             patch.object(experiment, 'start_experiment', side_effect=mock_start_experiment), \
             patch.object(experiment, 'determine_output_session_folder', return_value=temp_dir), \
             patch.object(experiment, 'save_launcher_metadata'), \
             patch.object(BaseLauncher, 'run_post_acquisition', return_value=True):
            
            result = experiment.run()
            
            assert result is True

    def test_run_repository_setup_failure(self, param_file):
        """Test experiment run with repository setup failure."""
        with patch('openscope_experimental_launcher.utils.git_manager.setup_repository', return_value=False), \
             patch('openscope_experimental_launcher.utils.rig_config.get_rig_config', return_value={'rig_id': 'test_rig'}):
            experiment = BaseLauncher(param_file=param_file)
            
            result = experiment.run()
            
            assert result is False

    def test_determine_output_session_folder_with_output_root_folder(self):
        """Test session directory determination with output_root_folder parameter."""
        experiment = BaseLauncher()
        experiment.params = {"output_root_folder": "/test/root"}
        experiment.subject_id = "test_mouse"
        
        result = experiment.determine_output_session_folder()
        
        assert result is not None
        assert result.startswith("/test/root")
        assert "test_mouse" in result

    def test_determine_output_session_folder_with_rig_config(self):
        """Test session directory determination using rig config output_root_folder merged into params."""
        experiment = BaseLauncher()
        # Simulate the rig_config being merged into params (as done in initialize_launcher)
        experiment.params = {"output_root_folder": "/rig/data"}
        experiment.rig_config = {"output_root_folder": "/rig/data"}  # Original source
        experiment.subject_id = "test_mouse"
        
        result = experiment.determine_output_session_folder()
        
        assert result is not None
        assert result.startswith("/rig/data")
        assert "test_mouse" in result

    def test_determine_output_session_folder_without_subject_id(self):
        """Test session directory determination without subject_id."""
        experiment = BaseLauncher()
        experiment.params = {"output_root_folder": "/test/root"}
        experiment.subject_id = None
        
        result = experiment.determine_output_session_folder()
        # Should return None when no subject_id is specified
        assert result is None

    def test_save_launcher_metadata(self, temp_dir):
        """Test saving launcher metadata."""
        experiment = BaseLauncher()
        experiment.params = {"subject_id": "test_mouse"}
        experiment.original_input_params = {"subject_id": "test_mouse"}
        experiment.original_param_file = None
        
        # This should not raise an exception
        experiment.save_launcher_metadata(temp_dir)
          # Check if metadata directory was created with expected files
        metadata_dir = os.path.join(temp_dir, "launcher_metadata")
        assert os.path.exists(metadata_dir)
          # Check for expected metadata files
        processed_params_file = os.path.join(metadata_dir, "processed_parameters.json")
        assert os.path.exists(processed_params_file)
        
        cmdline_file = os.path.join(metadata_dir, "command_line_arguments.json")
        assert os.path.exists(cmdline_file)
        
        input_params_file = os.path.join(metadata_dir, "input_parameters.json")
        assert os.path.exists(input_params_file)

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
            experiment.signal_handler(signal.SIGINT, None)
            mock_stop.assert_called_once()
            assert getattr(experiment, "_sigint_received", False) is True

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

 

    def test_mode_initialization(self):
        """Test initialization with different parameter configurations."""
        # Test initialization with param_file
        with patch('openscope_experimental_launcher.utils.rig_config.get_rig_config', return_value={'rig_id': 'test_rig'}):
            experiment_with_file = BaseLauncher(param_file=None)
            assert hasattr(experiment_with_file, 'params')
            assert isinstance(experiment_with_file.params, dict)
        
        # Test initialization with rig_config_path override
        with patch('openscope_experimental_launcher.utils.rig_config.get_rig_config', return_value={'rig_id': 'test_rig'}):
            experiment_with_rig_config = BaseLauncher(param_file=None, rig_config_path="/custom/path")
            assert hasattr(experiment_with_rig_config, 'params')
            assert isinstance(experiment_with_rig_config.params, dict)