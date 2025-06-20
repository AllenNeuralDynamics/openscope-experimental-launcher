"""
Tests for Python interface module.
"""

import pytest
import subprocess
import os
import sys
from unittest.mock import Mock, patch, MagicMock

from src.openscope_experimental_launcher.interfaces import python_interface


class TestPythonInterface:
    """Test cases for Python interface functions."""

    def test_setup_python_environment_success(self):
        """Test successful Python environment setup."""
        params = {'python_exe_path': 'python'}
        
        with patch.object(python_interface, 'check_installation', return_value=True):
            result = python_interface.setup_python_environment(params)
            assert result is True

    def test_setup_python_environment_failure(self):
        """Test Python environment setup failure."""
        params = {'python_exe_path': 'python'}
        
        with patch.object(python_interface, 'check_installation', return_value=False):
            result = python_interface.setup_python_environment(params)
            assert result is False

    def test_setup_python_environment_no_executable(self):
        """Test Python environment setup with no executable specified."""
        params = {}
        
        with patch.object(python_interface, 'check_installation', return_value=True):
            result = python_interface.setup_python_environment(params)
            assert result is True

    def test_setup_python_environment_with_venv(self):
        """Test Python environment setup with virtual environment."""
        params = {
            'python_exe_path': 'python',
            'virtual_env_path': '/test/venv'
        }
        
        with patch.object(python_interface, 'check_installation', return_value=True), \
             patch.object(python_interface, 'activate_virtual_environment', return_value=True):
            result = python_interface.setup_python_environment(params)
            assert result is True

    def test_setup_python_environment_venv_failure(self):
        """Test Python environment setup with virtual environment failure."""
        params = {
            'python_exe_path': 'python',
            'virtual_env_path': '/test/venv'
        }
        
        with patch.object(python_interface, 'check_installation', return_value=True), \
             patch.object(python_interface, 'activate_virtual_environment', return_value=False):
            result = python_interface.setup_python_environment(params)
            assert result is False

    def test_check_installation_success(self):
        """Test successful Python installation check."""
        mock_result = Mock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result):
            result = python_interface.check_installation('python')
            assert result is True

    def test_check_installation_default_executable(self):
        """Test Python installation check with default executable."""
        mock_result = Mock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result):
            result = python_interface.check_installation()
            assert result is True

    def test_check_installation_failure_returncode(self):
        """Test Python installation check with non-zero return code."""
        mock_result = Mock()
        mock_result.returncode = 1
        
        with patch('subprocess.run', return_value=mock_result):
            result = python_interface.check_installation('python')
            assert result is False

    def test_check_installation_timeout(self):
        """Test Python installation check with timeout."""
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('python', 30)):
            result = python_interface.check_installation('python')
            assert result is False

    def test_check_installation_file_not_found(self):
        """Test Python installation check with file not found."""
        with patch('subprocess.run', side_effect=FileNotFoundError):
            result = python_interface.check_installation('python')
            assert result is False

    def test_check_installation_os_error(self):
        """Test Python installation check with OS error."""
        with patch('subprocess.run', side_effect=OSError):
            result = python_interface.check_installation('python')
            assert result is False

    def test_activate_virtual_environment_success(self):
        """Test successful virtual environment activation."""
        with patch('os.path.exists', return_value=True), \
             patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            result = python_interface.activate_virtual_environment('/test/venv')
            assert result is True

    def test_activate_virtual_environment_not_found(self):
        """Test virtual environment activation with missing path."""
        with patch('os.path.exists', return_value=False):
            result = python_interface.activate_virtual_environment('/test/venv')
            assert result is False

    def test_activate_virtual_environment_failure(self):
        """Test virtual environment activation failure."""
        with patch('os.path.exists', return_value=True), \
             patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            result = python_interface.activate_virtual_environment('/test/venv')
            assert result is False

    def test_activate_virtual_environment_exception(self):
        """Test virtual environment activation with exception."""
        with patch('os.path.exists', return_value=True), \
             patch('subprocess.run', side_effect=Exception("Test exception")):
            result = python_interface.activate_virtual_environment('/test/venv')
            assert result is False

    def test_construct_python_arguments_basic(self):
        """Test basic Python argument construction."""
        params = {}
        args = python_interface.construct_python_arguments(params)
        assert isinstance(args, list)

    def test_construct_python_arguments_with_arguments(self):
        """Test Python argument construction with arguments."""
        params = {'script_arguments': ['-u', '--verbose']}
        args = python_interface.construct_python_arguments(params)
        
        assert '-u' in args
        assert '--verbose' in args

    def test_construct_python_arguments_with_python_args(self):
        """Test Python argument construction with Python-specific arguments."""
        params = {'python_arguments': ['-O', '-v']}
        args = python_interface.construct_python_arguments(params)
        
        assert '-O' in args
        assert '-v' in args

    def test_start_python_script_success(self):
        """Test successful Python script startup."""
        mock_process = MagicMock()
        
        with patch('subprocess.Popen', return_value=mock_process) as mock_popen, \
             patch('os.path.exists', return_value=True):
            process = python_interface.start_python_script(
                'test_script.py',
                'python',
                arguments=['-u'],
                output_path='/output'
            )
            
            assert process == mock_process
            mock_popen.assert_called_once()

    def test_start_python_script_file_not_found(self):
        """Test Python script startup with missing file."""
        with patch('os.path.exists', return_value=False):
            with pytest.raises(FileNotFoundError):
                python_interface.start_python_script('nonexistent.py')

    def test_start_python_script_subprocess_error(self):
        """Test Python script startup with subprocess error."""
        with patch('os.path.exists', return_value=True), \
             patch('subprocess.Popen', side_effect=OSError("Failed to start process")):
            with pytest.raises(OSError):
                python_interface.start_python_script('test_script.py')

    def test_start_python_script_default_executable(self):
        """Test Python script startup with default executable."""
        mock_process = MagicMock()
        
        with patch('subprocess.Popen', return_value=mock_process) as mock_popen, \
             patch('os.path.exists', return_value=True):
            process = python_interface.start_python_script('test_script.py')
            
            assert process == mock_process
            mock_popen.assert_called_once()
            
            # Check that default python executable was used
            call_args = mock_popen.call_args[0][0]
            assert call_args[0] == sys.executable

    def test_start_python_script_with_venv(self):
        """Test Python script startup with virtual environment."""
        mock_process = MagicMock()
        
        with patch('subprocess.Popen', return_value=mock_process) as mock_popen, \
             patch('os.path.exists', return_value=True):
            process = python_interface.start_python_script(
                'test_script.py',
                venv_path='/test/venv'
            )
            
            assert process == mock_process
            mock_popen.assert_called_once()

    def test_start_python_script_with_arguments(self):
        """Test Python script startup with arguments."""
        mock_process = MagicMock()
        
        with patch('subprocess.Popen', return_value=mock_process) as mock_popen, \
             patch('os.path.exists', return_value=True):
            process = python_interface.start_python_script(
                'test_script.py',
                arguments=['-u', '--verbose']
            )
            
            assert process == mock_process
            mock_popen.assert_called_once()
            
            # Check that arguments were passed
            call_args = mock_popen.call_args[0][0]
            assert '-u' in call_args
            assert '--verbose' in call_args

    def test_start_python_script_with_output_path(self):
        """Test Python script startup with output path."""
        mock_process = MagicMock()
        
        with patch('subprocess.Popen', return_value=mock_process) as mock_popen, \
             patch('os.path.exists', return_value=True):
            process = python_interface.start_python_script(
                'test_script.py',
                output_path='/test/output'
            )
            
            assert process == mock_process
            mock_popen.assert_called_once()
            
            # Check that environment variable was set
            call_kwargs = mock_popen.call_args[1]
            assert 'env' in call_kwargs
            assert call_kwargs['env']['OUTPUT_PATH'] == '/test/output'
