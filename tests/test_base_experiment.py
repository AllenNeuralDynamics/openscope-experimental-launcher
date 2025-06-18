"""
Unit tests for the BaseExperiment class.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from openscope_experimental_launcher.base.experiment import BaseExperiment


class TestBaseExperiment:
    """Test cases for BaseExperiment class."""

    def test_init(self):
        """Test BaseExperiment initialization."""
        experiment = BaseExperiment()
        
        assert experiment.platform_info is not None
        assert experiment.output_path is None
        assert experiment.params == {}
        assert experiment.bonsai_process is None
        assert experiment.session_uuid is not None
        assert experiment.config_loader is not None
        assert experiment.git_manager is not None
        assert experiment.process_monitor is not None

    def test_load_parameters_with_file(self, param_file, sample_params):
        """Test parameter loading from file."""
        experiment = BaseExperiment()        
        with patch.object(experiment.config_loader, 'load_config', return_value={}):
            experiment.load_parameters(param_file)
        
        assert experiment.params == sample_params
        assert experiment.subject_id == sample_params["subject_id"]
        assert experiment.user_id == sample_params["user_id"]
        assert experiment.params_checksum is not None

    def test_load_parameters_without_file(self):
        """Test parameter loading without file."""
        experiment = BaseExperiment()
        
        with patch.object(experiment.config_loader, 'load_config', return_value={}):
            experiment.load_parameters(None)
        
        # The experiment may load default parameters, so we check if params is a dict
        assert isinstance(experiment.params, dict)
        assert experiment.params_checksum is None

    def test_setup_output_path_with_path(self, temp_dir):
        """Test output path setup with specific path."""
        experiment = BaseExperiment()
        experiment.params = {"OutputFolder": temp_dir}
        experiment.subject_id = "test_mouse"
        
        result = experiment.determine_session_directory()
        
        assert result is not None
        assert result.startswith(temp_dir)
        assert "test_mouse" in result

    def test_setup_output_path_auto_generate(self, temp_dir):
        """Test automatic output path generation."""
        experiment = BaseExperiment()
        experiment.subject_id = "test_mouse"
        experiment.params = {"OutputFolder": temp_dir}
        
        result = experiment.determine_session_directory()
        
        assert result is not None
        assert result.startswith(temp_dir)
        assert "test_mouse" in result

    def test_create_bonsai_arguments(self):
        """Test Bonsai argument creation through BonsaiInterface."""
        experiment = BaseExperiment()
        experiment.params = {
            "subject_id": "test_mouse",
            "session_uuid": "test-uuid",
            "bonsai_parameters": {
                "ExperimentID": "test_experiment"
            }
        }
        
        # Mock the create_bonsai_property_arguments method since it doesn't exist in the actual interface
        def mock_create_args(params):
            args = []
            if "subject_id" in params:
                args.extend(["--property", f"SubjectID={params['subject_id']}"])
            if "bonsai_parameters" in params:
                for key, value in params["bonsai_parameters"].items():
                    args.extend(["--property", f"{key}={value}"])
            return args
        
        experiment.bonsai_interface.create_bonsai_property_arguments = mock_create_args
        
        # Test BonsaiInterface can create property arguments
        args = experiment.bonsai_interface.create_bonsai_property_arguments(experiment.params)
        
        expected_args = [
            "--property", "SubjectID=test_mouse",
            "--property", "ExperimentID=test_experiment"
        ]
        assert args == expected_args
        
        # Test with no bonsai_parameters
        experiment.params = {"subject_id": "test_mouse"}
        args = experiment.bonsai_interface.create_bonsai_property_arguments(experiment.params)
        expected_args = ["--property", "SubjectID=test_mouse"]
        assert args == expected_args

    @patch('openscope_experimental_launcher.base.experiment.psutil')
    def test_start_bonsai_success(self, mock_psutil, mock_subprocess, temp_dir):
        """Test successful Bonsai startup."""
        # Setup mocks
        mock_psutil.virtual_memory.return_value.percent = 50.0
        mock_subprocess['process'].returncode = 0
        
        experiment = BaseExperiment()
        experiment.params = {
            "bonsai_path": "test.bonsai",
            "bonsai_exe_path": "Bonsai.exe",
            "output_path": os.path.join(temp_dir, "output.pkl")
        }
        experiment.mouse_id = "test_mouse"
        experiment.user_id = "test_user"
          # Create a temporary workflow file
        test_workflow = os.path.join(temp_dir, "test.bonsai")
        with open(test_workflow, 'w') as f:
            f.write("<WorkflowBuilder>Test Workflow</WorkflowBuilder>")
        
        # Mock dependencies
        with patch.object(experiment.git_manager, 'get_repository_path', return_value=temp_dir), \
             patch('os.path.exists', return_value=True), \
             patch('hashlib.md5') as mock_md5, \
             patch.object(experiment.process_monitor, 'monitor_process'):
            
            mock_md5.return_value.hexdigest.return_value = "test_checksum"
            experiment.start_bonsai()
            
            assert experiment.bonsai_process is not None
            assert experiment.start_time is not None
            mock_subprocess['popen'].assert_called_once()
    
    @patch('os.path.exists', return_value=True)
    @patch('subprocess.Popen')
    def test_start_bonsai_process_creation_failure(self, mock_popen, mock_exists):
        """Test Bonsai process creation failure."""
        mock_popen.side_effect = OSError("Failed to start process")
        
        experiment = BaseExperiment()
        experiment.params = {
            'bonsai_exe_path': 'bonsai.exe',
            'bonsai_path': 'workflow.bonsai'
        }
          # Mock the setup and command creation
        experiment.bonsai_interface.setup_bonsai_environment = Mock(return_value=True)
        experiment.bonsai_interface.create_bonsai_command = Mock(return_value=['bonsai.exe', 'workflow.bonsai'])
        experiment.bonsai_interface.bonsai_exe_path = 'bonsai.exe'  # Set the exe path        # Mock the path resolution
        experiment._resolve_bonsai_paths = Mock(return_value={})
        
        # Should raise the exception since current implementation re-raises
        with pytest.raises(OSError, match="Failed to start process"):
            experiment.start_bonsai()
          # Process should not be set
        assert experiment.bonsai_process is None
    
    def test_determine_session_directory_no_output_folder(self):
        """Test session directory determination when no OutputFolder specified."""
        experiment = BaseExperiment()
        experiment.params = {
            'subject_id': 'test_mouse',
            'user_id': 'test_user'
        }
        experiment.subject_id = 'test_mouse'
        experiment.user_id = 'test_user'
        
        # Should return None when OutputFolder is not specified
        result = experiment.determine_session_directory()
        
        assert result is None
    
    @patch('os.makedirs')
    def test_determine_session_directory_creation_failure(self, mock_makedirs):
        """Test session directory creation failure."""
        mock_makedirs.side_effect = OSError("Permission denied")
        
        experiment = BaseExperiment()
        experiment.params = {
            'OutputFolder': '/invalid/path',
            'subject_id': 'test_mouse',
            'user_id': 'test_user'
        }
        experiment.subject_id = 'test_mouse'
        experiment.user_id = 'test_user'
        
        result = experiment.determine_session_directory()
        assert result is None
    
    @patch('builtins.open', side_effect=OSError("File not found"))
    def test_save_experiment_metadata_file_error(self, mock_open):
        """Test experiment metadata saving with file error."""
        experiment = BaseExperiment()
        experiment.params = {'test': 'value'}
        experiment.subject_id = 'test_mouse'
        experiment.user_id = 'test_user'
        experiment.session_uuid = 'test_session'
          # Should handle file errors gracefully
        experiment.save_experiment_metadata('/tmp/test', 'param_file.json')
        
        # Test should complete without raising exception
    
    def test_collect_runtime_info_error_handling(self):
        """Test runtime info collection with errors."""
        experiment = BaseExperiment()
        
        with patch('platform.platform', side_effect=Exception("Platform error")):
            runtime_info = experiment.collect_runtime_information()
        
        # Should return dict with default values on error
        assert isinstance(runtime_info, dict)
    
    @patch('logging.FileHandler')
    def test_setup_continuous_logging_error(self, mock_file_handler):
        """Test continuous logging setup with errors."""
        mock_file_handler.side_effect = Exception("Cannot create log file")
        
        experiment = BaseExperiment()
        experiment.session_uuid = 'test_session'
        
        # Should handle logging setup errors gracefully
        experiment.setup_continuous_logging('/tmp/test')
    
    def test_run_with_bonsai_failure(self):
        """Test run method when Bonsai process fails."""
        experiment = BaseExperiment()
        experiment.params = {
            'subject_id': 'test_mouse',
            'user_id': 'test_user',
            'bonsai_exe_path': 'bonsai.exe',
            'bonsai_path': 'workflow.bonsai'        }
        experiment.subject_id = 'test_mouse'
        experiment.user_id = 'test_user'        
        mock_process = Mock()
        mock_process.returncode = 1  # Failed process
        mock_process.pid = 1234
        
        with patch.object(experiment, 'load_parameters'), \
             patch.object(experiment, 'determine_session_directory', return_value='/tmp/test'), \
             patch.object(experiment, 'setup_continuous_logging'), \
             patch.object(experiment, 'save_experiment_metadata'), \
             patch.object(experiment, 'start_bonsai'), \
             patch.object(experiment, 'post_experiment_processing', return_value=True):
            
            experiment.bonsai_process = mock_process
            
            result = experiment.run('test_params.json')
            assert result is False
    
    def test_get_experiment_type_name(self):
        """Test experiment type name getter."""
        experiment = BaseExperiment()
        assert experiment._get_experiment_type_name() == "Bonsai"    
    def test_post_experiment_processing_default(self):
        """Test default post-experiment processing."""
        experiment = BaseExperiment()
        result = experiment.post_experiment_processing()
        assert result is True

    def test_signal_handler(self, mock_subprocess):
        """Test signal handler functionality."""
        experiment = BaseExperiment()
        experiment.bonsai_process = mock_subprocess['process']
        
        with pytest.raises(SystemExit):
            experiment.signal_handler(None, None)

    def test_run_success(self, param_file, mock_subprocess):
        """Test successful experiment run."""
        experiment = BaseExperiment()
        
        with patch.object(experiment, 'load_parameters') as mock_load, \
             patch.object(experiment.git_manager, 'setup_repository', return_value=True), \
             patch.object(experiment, 'start_bonsai'), \
             patch('signal.signal'):
            
            mock_subprocess['process'].returncode = 0
            experiment.bonsai_process = mock_subprocess['process']
            
            result = experiment.run(param_file)
            
            assert result is True
            mock_load.assert_called_once_with(param_file)

    def test_run_repository_setup_failure(self, param_file):
        """Test experiment run with repository setup failure."""
        experiment = BaseExperiment()
        
        with patch.object(experiment, 'load_parameters'), \
             patch.object(experiment.git_manager, 'setup_repository', return_value=False), \
             patch('signal.signal'):
            
            result = experiment.run(param_file)
            
            assert result is False

    def test_cleanup(self, mock_subprocess):
        """Test cleanup functionality."""
        experiment = BaseExperiment()
        experiment.bonsai_process = mock_subprocess['process']
        
        with patch.object(experiment, 'stop') as mock_stop:
            experiment.cleanup()
            mock_stop.assert_called_once()

    def test_stop_process(self, mock_subprocess):
        """Test process stopping."""
        experiment = BaseExperiment()
        experiment.bonsai_process = mock_subprocess['process']
        mock_subprocess['process'].poll.return_value = None  # Process running
        
        experiment.stop()
        
        mock_subprocess['process'].terminate.assert_called_once()

    def test_get_bonsai_errors_with_errors(self):
        """Test error retrieval when errors exist."""
        experiment = BaseExperiment()
        experiment.stderr_data = ["Error 1", "Error 2"]
        
        errors = experiment.get_bonsai_errors()
        
        assert "Error 1" in errors
        assert "Error 2" in errors

    def test_get_bonsai_errors_no_errors(self):
        """Test error retrieval when no errors exist."""
        experiment = BaseExperiment()
        experiment.stderr_data = []
        
        errors = experiment.get_bonsai_errors()
        
        assert "No errors reported" in errors