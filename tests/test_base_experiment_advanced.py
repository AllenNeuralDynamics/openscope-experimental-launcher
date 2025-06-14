"""
Comprehensive tests for BaseExperiment class to significantly boost coverage.
Targets error handling, edge cases, platform-specific code, and signal handling.
"""

import os
import pytest
import signal
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock, mock_open
import datetime

from openscope_experimental_launcher.base.experiment import BaseExperiment


class TestBaseExperimentComprehensive:
    """Comprehensive tests to boost BaseExperiment coverage from 72% to 90%+."""
    
    def test_init_windows_modules_unavailable(self):
        """Test initialization when Windows modules are not available."""
        with patch('openscope_experimental_launcher.base.experiment.WINDOWS_MODULES_AVAILABLE', False):
            experiment = BaseExperiment()
            assert experiment.hJob is None
            assert experiment.platform_info is not None

    @patch('openscope_experimental_launcher.base.experiment.win32job.CreateJobObject')
    def test_setup_windows_job_success(self, mock_create_job):
        """Test successful Windows job object creation."""
        with patch('openscope_experimental_launcher.base.experiment.WINDOWS_MODULES_AVAILABLE', True):
            mock_job = Mock()
            mock_create_job.return_value = mock_job
            
            with patch('openscope_experimental_launcher.base.experiment.win32job.QueryInformationJobObject') as mock_query, \
                 patch('openscope_experimental_launcher.base.experiment.win32job.SetInformationJobObject') as mock_set:
                mock_query.return_value = {'BasicLimitInformation': {'LimitFlags': 0}}
                
                experiment = BaseExperiment()
                assert experiment.hJob == mock_job

    @patch('openscope_experimental_launcher.base.experiment.win32job.CreateJobObject')
    def test_setup_windows_job_failure(self, mock_create_job):
        """Test Windows job object creation failure."""
        with patch('openscope_experimental_launcher.base.experiment.WINDOWS_MODULES_AVAILABLE', True):
            mock_create_job.side_effect = Exception("Failed to create job")
            
            experiment = BaseExperiment()
            assert experiment.hJob is None

    def test_collect_runtime_information_no_params(self):
        """Test runtime information collection when no params are set."""
        experiment = BaseExperiment()
        experiment.params = {}  # No existing parameters
        
        with patch('builtins.input', side_effect=['test_mouse', 'test_user']):
            runtime_info = experiment.collect_runtime_information()
            
            assert runtime_info['subject_id'] == 'test_mouse'
            assert runtime_info['experimenter_name'] == 'test_user'

    def test_collect_runtime_information_eof_error(self):
        """Test runtime information collection with EOFError (no input available)."""
        experiment = BaseExperiment()
        experiment.params = {}
        
        with patch('builtins.input', side_effect=EOFError()):
            runtime_info = experiment.collect_runtime_information()
            
            assert runtime_info['subject_id'] == 'test_subject'
            assert runtime_info['experimenter_name'] == 'test_experimenter'

    def test_collect_runtime_information_os_error(self):
        """Test runtime information collection with OSError."""
        experiment = BaseExperiment()
        experiment.params = {}
        
        with patch('builtins.input', side_effect=OSError("Input not available")):
            runtime_info = experiment.collect_runtime_information()
            
            assert runtime_info['subject_id'] == 'test_subject'
            assert runtime_info['experimenter_name'] == 'test_experimenter'

    def test_collect_runtime_information_existing_params(self):
        """Test runtime information collection when params already exist."""
        experiment = BaseExperiment()
        experiment.params = {
            'mouse_id': 'existing_mouse',
            'user_id': 'existing_user'
        }
        
        runtime_info = experiment.collect_runtime_information()
        
        # Should return empty dict since params already exist
        assert runtime_info == {}

    def test_load_parameters_no_file(self):
        """Test parameter loading with no file provided."""
        experiment = BaseExperiment()
        
        with patch.object(experiment, 'collect_runtime_information', return_value={'subject_id': 'test'}):
            experiment.load_parameters(None)
            
            # Should have subject_id from runtime info, plus other defaults
            assert 'subject_id' in experiment.params
            assert experiment.params['subject_id'] == 'test'
            assert experiment.mouse_id == 'test'

    def test_load_parameters_fallback_to_config(self):
        """Test parameter loading that falls back to config values."""
        experiment = BaseExperiment()
        
        with patch.object(experiment, 'collect_runtime_information', return_value={}), \
             patch.object(experiment.config_loader, 'load_config', return_value={
                 'Behavior': {'mouse_id': 'config_mouse', 'user_id': 'config_user'}
             }):
            
            experiment.load_parameters(None)
            
            assert experiment.mouse_id == 'config_mouse'
            assert experiment.user_id == 'config_user'

    def test_setup_output_path_specific_path(self):
        """Test output path setup with specific path provided."""
        experiment = BaseExperiment()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "specific_output.pkl")
            
            result = experiment.setup_output_path(output_path)
            
            assert result == output_path
            assert experiment.session_output_path == output_path

    @patch('os.makedirs')
    def test_setup_output_path_create_directory(self, mock_makedirs):
        """Test output path setup that creates new directory."""
        experiment = BaseExperiment()
        experiment.mouse_id = "test_mouse"
        
        with patch('os.path.isdir', return_value=False):
            output_path = "/new/dir/output.pkl"
            result = experiment.setup_output_path(output_path)
            
            mock_makedirs.assert_called_once()
            assert result == output_path

    def test_setup_output_path_auto_generate(self):
        """Test automatic output path generation."""
        experiment = BaseExperiment()
        experiment.mouse_id = "test_mouse"
        experiment.params = {"output_directory": "test_data"}
        
        with patch('os.path.isdir', return_value=True):
            result = experiment.setup_output_path()
            
            assert "test_mouse" in result
            assert result.endswith(".pkl")
            assert "test_data" in result

    def test_create_bonsai_arguments_with_parameters(self):
        """Test Bonsai argument creation with custom parameters."""
        experiment = BaseExperiment()
        experiment.params = {
            "bonsai_parameters": {
                "StimType": "gratings",
                "Duration": 300,
                "MouseID": "test_mouse"
            }
        }
        
        args = experiment.create_bonsai_arguments()
        
        expected_args = [
            "--property", "StimType=gratings",
            "--property", "Duration=300", 
            "--property", "MouseID=test_mouse"
        ]
        assert args == expected_args

    def test_create_bonsai_arguments_no_parameters(self):
        """Test Bonsai argument creation with no custom parameters."""
        experiment = BaseExperiment()
        experiment.params = {}
        
        args = experiment.create_bonsai_arguments()
        
        assert args == []

    def test_get_bonsai_args_missing_path(self):
        """Test Bonsai argument construction with missing workflow path."""
        experiment = BaseExperiment()
        experiment.params = {}
        
        with pytest.raises(ValueError, match="No Bonsai workflow path specified"):
            experiment._get_bonsai_args()

    def test_get_bonsai_args_missing_workflow_file(self):
        """Test Bonsai argument construction with missing workflow file."""
        experiment = BaseExperiment()
        experiment.params = {'bonsai_path': '/nonexistent/workflow.bonsai'}
        
        with patch('os.path.exists', return_value=False), \
             patch.object(experiment.git_manager, 'get_repository_path', return_value=None):
            
            with pytest.raises(ValueError, match="Bonsai workflow not found"):
                experiment._get_bonsai_args()

    @patch('builtins.open', new_callable=mock_open, read_data=b'workflow content')
    def test_get_bonsai_args_relative_paths(self, mock_file):
        """Test Bonsai argument construction with relative paths."""
        experiment = BaseExperiment()
        experiment.params = {
            'bonsai_path': 'workflow.bonsai',
            'bonsai_exe_path': 'Bonsai.exe'
        }
        
        with patch('os.path.exists', return_value=True), \
             patch('os.path.isabs', return_value=False), \
             patch.object(experiment.git_manager, 'get_repository_path', return_value='/repo'):
            
            args = experiment._get_bonsai_args()
            
            # Use os.path.join for cross-platform compatibility
            expected_exe = os.path.join('/repo', 'Bonsai.exe')
            expected_workflow = os.path.join('/repo', 'workflow.bonsai')
            assert expected_exe in args
            assert expected_workflow in args

    def test_get_bonsai_errors_no_errors(self):
        """Test getting Bonsai errors when none exist."""
        experiment = BaseExperiment()
        experiment.stderr_data = []
        
        result = experiment.get_bonsai_errors()
        
        assert result == "No errors reported by Bonsai."

    def test_get_bonsai_errors_with_errors(self):
        """Test getting Bonsai errors when they exist."""
        experiment = BaseExperiment()
        experiment.stderr_data = ["Error 1", "Error 2", "Error 3"]
        
        result = experiment.get_bonsai_errors()
        
        assert result == "Error 1\nError 2\nError 3"

    def test_assign_to_job_object_success(self):
        """Test successful assignment to Windows job object."""
        experiment = BaseExperiment()
        experiment.hJob = Mock()
        experiment.bonsai_process = Mock()
        experiment.bonsai_process.pid = 12345
        
        with patch('openscope_experimental_launcher.base.experiment.WINDOWS_MODULES_AVAILABLE', True), \
             patch('openscope_experimental_launcher.base.experiment.win32api.OpenProcess') as mock_open_proc, \
             patch('openscope_experimental_launcher.base.experiment.win32job.AssignProcessToJobObject') as mock_assign:
            
            mock_handle = Mock()
            mock_open_proc.return_value = mock_handle
            
            experiment._assign_to_job_object()
            
            mock_assign.assert_called_once_with(experiment.hJob, mock_handle)

    def test_assign_to_job_object_failure(self):
        """Test assignment to Windows job object failure."""
        experiment = BaseExperiment()
        experiment.hJob = Mock()
        experiment.bonsai_process = Mock()
        experiment.bonsai_process.pid = 12345
        
        with patch('openscope_experimental_launcher.base.experiment.WINDOWS_MODULES_AVAILABLE', True), \
             patch('openscope_experimental_launcher.base.experiment.win32api.OpenProcess', side_effect=Exception("Access denied")):
            
            # Should not raise exception, just log warning
            experiment._assign_to_job_object()

    def test_monitor_bonsai_error_return_code(self):
        """Test Bonsai monitoring with error return code."""
        experiment = BaseExperiment()
        experiment.bonsai_process = Mock()
        experiment.bonsai_process.returncode = 1
        experiment.stderr_data = ["Critical error occurred"]
        experiment.mouse_id = "test_mouse"
        experiment.user_id = "test_user"
        experiment._output_threads = []
        
        with patch.object(experiment.process_monitor, 'monitor_process'):
            experiment._monitor_bonsai()

    def test_monitor_bonsai_success_with_warnings(self):
        """Test successful Bonsai monitoring with warnings."""
        experiment = BaseExperiment()
        experiment.bonsai_process = Mock()
        experiment.bonsai_process.returncode = 0
        experiment.stderr_data = ["Warning: Something minor"]
        experiment.mouse_id = "test_mouse"
        experiment.user_id = "test_user"
        experiment._output_threads = []
        experiment.start_time = datetime.datetime.now()
        
        with patch.object(experiment.process_monitor, 'monitor_process'):
            experiment._monitor_bonsai()
            
            assert experiment.stop_time is not None

    def test_monitor_bonsai_exception(self):
        """Test Bonsai monitoring with exception."""
        experiment = BaseExperiment()
        experiment.bonsai_process = Mock()
        experiment._output_threads = []
        
        with patch.object(experiment.process_monitor, 'monitor_process', side_effect=Exception("Monitor failed")), \
             patch.object(experiment, 'stop'):
            
            experiment._monitor_bonsai()

    def test_kill_process_not_running(self):
        """Test killing process when it's not running."""
        experiment = BaseExperiment()
        experiment.bonsai_process = Mock()
        experiment.bonsai_process.poll.return_value = 0  # Already finished
        
        # Should not raise exception
        experiment.kill_process()

    @patch('subprocess.call')
    def test_kill_process_windows_force_kill(self, mock_call):
        """Test force killing process on Windows."""
        experiment = BaseExperiment()
        experiment.bonsai_process = Mock()
        experiment.bonsai_process.poll.return_value = None  # Still running
        experiment.bonsai_process.pid = 12345
        
        with patch('openscope_experimental_launcher.base.experiment.WINDOWS_MODULES_AVAILABLE', True):
            experiment.kill_process()
            
            experiment.bonsai_process.kill.assert_called_once()
            mock_call.assert_called_once_with(['taskkill', '/F', '/T', '/PID', '12345'])

    def test_stop_no_process(self):
        """Test stop method when no process is running."""
        experiment = BaseExperiment()
        experiment.bonsai_process = None
        
        # Should not raise exception
        experiment.stop()

    def test_stop_already_finished(self):
        """Test stop method when process already finished."""
        experiment = BaseExperiment()
        experiment.bonsai_process = Mock()
        experiment.bonsai_process.poll.return_value = 0  # Already finished
        
        # Should not raise exception
        experiment.stop()

    def test_stop_exception_handling(self):
        """Test stop method exception handling."""
        experiment = BaseExperiment()
        experiment.bonsai_process = Mock()
        experiment.bonsai_process.poll.return_value = None
        experiment.bonsai_process.terminate.side_effect = Exception("Terminate failed")
        
        # Should not raise exception
        experiment.stop()

    def test_signal_handler(self):
        """Test signal handler."""
        experiment = BaseExperiment()
        
        with patch.object(experiment, 'stop'), \
             patch('sys.exit') as mock_exit:
            
            experiment.signal_handler(signal.SIGINT, None)
            
            mock_exit.assert_called_once_with(0)

    def test_run_repository_setup_failure(self):
        """Test run method when repository setup fails."""
        experiment = BaseExperiment()
        
        with patch.object(experiment, 'load_parameters'), \
             patch.object(experiment.git_manager, 'setup_repository', return_value=False), \
             patch.object(experiment, 'stop'):
            
            result = experiment.run("test_params.json")
            
            assert result is False

    def test_run_bonsai_failure(self):
        """Test run method when Bonsai fails."""
        experiment = BaseExperiment()
        experiment.bonsai_process = Mock()
        experiment.bonsai_process.returncode = 1
        
        with patch.object(experiment, 'load_parameters'), \
             patch.object(experiment.git_manager, 'setup_repository', return_value=True), \
             patch.object(experiment, 'start_bonsai'), \
             patch.object(experiment, 'stop'):
            
            result = experiment.run("test_params.json")
            
            assert result is False

    def test_run_post_processing_failure(self):
        """Test run method when post-processing fails."""
        experiment = BaseExperiment()
        experiment.bonsai_process = Mock()
        experiment.bonsai_process.returncode = 0
        
        with patch.object(experiment, 'load_parameters'), \
             patch.object(experiment.git_manager, 'setup_repository', return_value=True), \
             patch.object(experiment, 'start_bonsai'), \
             patch.object(experiment, 'post_experiment_processing', return_value=False), \
             patch.object(experiment, 'stop'):
            
            result = experiment.run("test_params.json")
            
            # Should still return True even if post-processing fails
            assert result is True

    def test_run_exception_handling(self):
        """Test run method exception handling."""
        experiment = BaseExperiment()
        
        with patch.object(experiment, 'load_parameters', side_effect=Exception("Load failed")), \
             patch.object(experiment, 'stop'):
            
            result = experiment.run("test_params.json")
            
            assert result is False

    def test_cleanup(self):
        """Test cleanup method."""
        experiment = BaseExperiment()
        
        with patch.object(experiment, 'stop'):
            experiment.cleanup()

    def test_post_experiment_processing_default(self):
        """Test default post-experiment processing."""
        experiment = BaseExperiment()
        
        result = experiment.post_experiment_processing()
        
        assert result is True