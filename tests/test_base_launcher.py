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

    def test_collect_runtime_information(self):
        """Test runtime information collection."""
        with patch('openscope_experimental_launcher.utils.rig_config.get_rig_config', return_value={'rig_id': 'test_rig'}):
            experiment = BaseLauncher()
        # Clear the rig config from params to test collection
        experiment.params = {}
        runtime_info = experiment.collect_runtime_information()
        assert isinstance(runtime_info, dict)        # The current implementation only collects subject_id and user_id if not already in params
        assert "subject_id" in runtime_info or "user_id" in runtime_info

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
        """Test successful process start via BaseLauncher (should fail without implementation)."""
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
        
        # BaseLauncher.create_process should raise NotImplementedError
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
            
            assert result is None  # Method returns None
            
    def test_get_process_errors(self):
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
        """Test post-experiment processing functionality."""
        experiment = BaseLauncher()
        # Test the run_post_processing static method instead
        with patch('os.path.exists', return_value=True):
            result = BaseLauncher.run_post_processing("/tmp/test_session")
            
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
             patch.object(BaseLauncher, 'run_post_processing', return_value=True):
            
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
        
        # Mock the AIND_DATA_SCHEMA_AVAILABLE constant to simulate it not being available
        with patch('openscope_experimental_launcher.launchers.base_launcher.AIND_DATA_SCHEMA_AVAILABLE', False):
            result = experiment.create_session_file(output_dir)
        
        # Should return False when schema is not available
        assert result is False        # session.json should not be created
        session_file = tmp_path / "session.json"
        assert not session_file.exists()
    
    def test_create_session_file_with_schema(self, tmp_path):
        """Test session file creation with aind-data-schema available."""
        
        experiment = BaseLauncher()
        experiment.start_time = datetime.datetime.now()
        experiment.stop_time = datetime.datetime.now()
        experiment.params = {"subject_id": "test_mouse"}
        experiment.subject_id = "test_mouse"
        experiment.user_id = "test_user"
        experiment.session_uuid = "test_session"
        
        # Initialize rig_config for session creation
        experiment.rig_config = {"rig_id": "test_rig", "output_root_folder": "/tmp"}
        
        output_dir = str(tmp_path)
        
        # Test the actual session creation (aind-data-schema should be available)
        result = experiment.create_session_file(output_dir)
        
        # Should return True when session is created successfully
        assert result is True
        
        # session.json should be created
        session_file = tmp_path / "session.json"
        assert session_file.exists()
        
        # Verify the contents - the new system creates a proper aind-data-schema Session object
        import json
        with open(session_file, 'r') as f:
            session_data = json.load(f)
        
        # Check for key fields that should be present in the aind-data-schema Session
        assert session_data["subject_id"] == "test_mouse"
        assert "session_start_time" in session_data
        assert "session_end_time" in session_data
        assert "data_streams" in session_data

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

    def test_argument_parser_modes(self):
        """Test argument parser with current implementation."""
        parser = BaseLauncher.create_argument_parser()
        
        # Test with param file
        args = parser.parse_args(['params.json'])
        assert args.param_file == 'params.json'
        
        # Test without param file (optional)
        args = parser.parse_args([])
        assert args.param_file is None
        
        # Test with description
        parser_with_desc = BaseLauncher.create_argument_parser("Custom description")
        assert parser_with_desc.description == "Custom description"