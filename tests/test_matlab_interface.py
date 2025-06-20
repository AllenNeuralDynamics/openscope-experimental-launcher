"""
Tests for MATLAB interface module.
"""

import pytest
import subprocess
from unittest.mock import Mock, patch, MagicMock

from src.openscope_experimental_launcher.interfaces import matlab_interface


class TestMATLABInterface:
    """Test cases for MATLAB interface functions."""

    def test_setup_matlab_environment_success(self):
        """Test successful MATLAB environment setup."""
        params = {'matlab_exe_path': 'matlab'}
        
        with patch.object(matlab_interface, 'check_installation', return_value=True):
            result = matlab_interface.setup_matlab_environment(params)
            assert result is True

    def test_setup_matlab_environment_failure(self):
        """Test MATLAB environment setup failure."""
        params = {'matlab_exe_path': 'matlab'}
        
        with patch.object(matlab_interface, 'check_installation', return_value=False):
            result = matlab_interface.setup_matlab_environment(params)
            assert result is False

    def test_check_installation_success(self):
        """Test successful MATLAB installation check."""
        mock_result = Mock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result):
            result = matlab_interface.check_installation('matlab')
            assert result is True

    def test_check_installation_failure_returncode(self):
        """Test MATLAB installation check with non-zero return code."""
        mock_result = Mock()
        mock_result.returncode = 1
        
        with patch('subprocess.run', return_value=mock_result):
            result = matlab_interface.check_installation('matlab')
            assert result is False

    def test_check_installation_timeout(self):
        """Test MATLAB installation check with timeout."""
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('matlab', 30)):
            result = matlab_interface.check_installation('matlab')
            assert result is False

    def test_check_installation_file_not_found(self):
        """Test MATLAB installation check with file not found."""
        with patch('subprocess.run', side_effect=FileNotFoundError):
            result = matlab_interface.check_installation('matlab')
            assert result is False

    def test_check_installation_os_error(self):
        """Test MATLAB installation check with OS error."""
        with patch('subprocess.run', side_effect=OSError):
            result = matlab_interface.check_installation('matlab')
            assert result is False

    def test_construct_matlab_arguments_basic(self):
        """Test basic MATLAB argument construction."""
        params = {}
        args = matlab_interface.construct_matlab_arguments(params)
        assert '-batch' in args

    def test_construct_matlab_arguments_with_custom_args(self):
        """Test MATLAB argument construction with custom arguments."""
        params = {'script_arguments': ['-nosplash', '-nodesktop']}
        args = matlab_interface.construct_matlab_arguments(params)
        
        assert '-batch' in args
        assert '-nosplash' in args
        assert '-nodesktop' in args

    def test_start_matlab_script_success(self):
        """Test successful MATLAB script startup."""
        mock_process = MagicMock()
        
        with patch('subprocess.Popen', return_value=mock_process) as mock_popen, \
             patch('os.path.exists', return_value=True):
            process = matlab_interface.start_matlab_script(
                'test_script.m', 
                'matlab',
                arguments=['-batch'],
                output_path='C:/output'
            )
            
            assert process == mock_process
            mock_popen.assert_called_once()

    def test_start_matlab_script_with_arguments(self):
        """Test MATLAB script startup with additional arguments."""
        mock_process = MagicMock()
        
        with patch('subprocess.Popen', return_value=mock_process) as mock_popen, \
             patch('os.path.exists', return_value=True):
            process = matlab_interface.start_matlab_script(
                'test_script.m',
                'matlab',
                arguments=['-batch', '-nosplash'],
                output_path='C:/output'
            )
            
            assert process == mock_process
            mock_popen.assert_called_once()
            
            # Check that arguments were passed correctly
            call_args = mock_popen.call_args[0][0]
            assert 'matlab' in call_args
            assert '-batch' in call_args
            assert '-nosplash' in call_args

    def test_start_matlab_script_default_exe(self):
        """Test MATLAB script startup with default executable."""
        mock_process = MagicMock()
        
        with patch('subprocess.Popen', return_value=mock_process) as mock_popen, \
             patch('os.path.exists', return_value=True):
            process = matlab_interface.start_matlab_script('test_script.m')
            
            assert process == mock_process
            mock_popen.assert_called_once()
            
            # Check that default matlab executable was used
            call_args = mock_popen.call_args[0][0]
            assert 'matlab' in call_args

    def test_start_matlab_script_file_not_found(self):
        """Test MATLAB script startup with missing file."""
        with patch('os.path.exists', return_value=False):
            with pytest.raises(FileNotFoundError):
                matlab_interface.start_matlab_script('nonexistent.m')

    def test_start_matlab_script_subprocess_error(self):
        """Test MATLAB script startup with subprocess error."""
        with patch('os.path.exists', return_value=True), \
             patch('subprocess.Popen', side_effect=OSError("Failed to start process")):
            with pytest.raises(OSError):
                matlab_interface.start_matlab_script('test_script.m')
