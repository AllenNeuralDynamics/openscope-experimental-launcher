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
        
        # Since the JSON file already contains experimenter_name and mouse_id,
        # runtime collection should NOT add subject_id or override experimenter_name
        for key, value in sample_params.items():
            assert experiment.params[key] == value
        
        # Check that mouse_id and user_id are properly extracted
        assert experiment.mouse_id == sample_params.get("mouse_id", "")
        assert experiment.user_id == sample_params.get("experimenter_name", sample_params.get("user_id", ""))
        assert experiment.params_checksum is not None

    def test_load_parameters_without_file(self):
        """Test parameter loading without file."""
        experiment = BaseExperiment()
        
        with patch.object(experiment.config_loader, 'load_config', return_value={}):
            experiment.load_parameters(None)
        
        # Should have runtime information even without file
        assert isinstance(experiment.params, dict)
        assert 'subject_id' in experiment.params
        assert 'experimenter_name' in experiment.params
        assert experiment.params_checksum is None

    def test_generate_output_directory(self):
        """Test output directory generation using AIND data schema."""
        experiment = BaseExperiment()
        experiment.mouse_id = "test_mouse"
        
        root_folder = "C:/data"
        result = experiment.generate_output_directory(root_folder, "test_mouse")
        
        # Should contain the root folder and follow AIND naming pattern
        assert result.startswith(root_folder)
        assert "test_mouse" in result
        
    def test_prepare_bonsai_parameters_output_folder(self):
        """Test that _prepare_bonsai_parameters generates OutputFolder correctly."""
        experiment = BaseExperiment()
        experiment.mouse_id = "test_mouse"
        experiment.params = {
            "bonsai_parameters": {
                "RootFolder": "C:/data",
                "Subject": "test_mouse"
            }
        }
        
        result = experiment._prepare_bonsai_parameters()
        
        # Should have OutputFolder instead of RootFolder
        assert "OutputFolder" in result["bonsai_parameters"]
        assert "RootFolder" not in result["bonsai_parameters"]
        assert result["bonsai_parameters"]["Subject"] == "test_mouse"

    def test_create_bonsai_arguments(self):
        """Test Bonsai argument creation through BonsaiInterface."""
        experiment = BaseExperiment()
        experiment.params = {
            "mouse_id": "test_mouse",
            "session_uuid": "test-uuid",
            "bonsai_parameters": {
                "SubjectID": "test_mouse",
                "ExperimentID": "test_experiment"
            }
        }
        
        # Test BonsaiInterface can create property arguments
        args = experiment.bonsai_interface.create_bonsai_property_arguments(experiment.params)
        
        expected_args = [
            "--property", "SubjectID=test_mouse",
            "--property", "ExperimentID=test_experiment"
        ]
        assert args == expected_args
        
        # Test with no bonsai_parameters
        experiment.params = {}
        args = experiment.bonsai_interface.create_bonsai_property_arguments(experiment.params)
        assert args == []  # Should be empty when no bonsai_parameters specified

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

    def test_get_platform_info(self):
        """Test platform information gathering."""
        experiment = BaseExperiment()
        platform_info = experiment._get_platform_info()
        
        assert 'python' in platform_info
        assert 'os' in platform_info
        assert 'hardware' in platform_info
        assert 'computer_name' in platform_info
        assert 'rig_id' in platform_info

    @patch('openscope_experimental_launcher.base.experiment.WINDOWS_MODULES_AVAILABLE', True)
    @patch('openscope_experimental_launcher.base.experiment.win32job')
    def test_setup_windows_job_success(self, mock_win32job):
        """Test Windows job object setup."""
        mock_win32job.CreateJobObject.return_value = "test_job"
        mock_win32job.QueryInformationJobObject.return_value = {
            'BasicLimitInformation': {'LimitFlags': 0}
        }
        
        experiment = BaseExperiment()
        
        assert experiment.hJob == "test_job"
        mock_win32job.CreateJobObject.assert_called_once()

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