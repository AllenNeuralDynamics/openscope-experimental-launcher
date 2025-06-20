"""
Tests for MATLAB launcher module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.openscope_experimental_launcher.launchers import matlab_launcher


class TestMATLABLauncher:
    """Test cases for MATLAB launcher."""

    def test_init_default_params(self):
        """Test MATLABLauncher initialization with default parameters."""
        launcher = matlab_launcher.MATLABLauncher()
        
        assert launcher is not None
        assert hasattr(launcher, 'logger')

    def test_init_with_params(self):
        """Test MATLABLauncher initialization with parameters."""
        params = {
            'matlab_exe_path': '/usr/local/bin/matlab',
            'script_path': '/test/script.m',
            'output_path': '/test/output'
        }
        
        launcher = matlab_launcher.MATLABLauncher(params)
        
        assert launcher is not None
        assert hasattr(launcher, 'logger')

    def test_create_process_success(self):
        """Test successful process creation."""
        params = {
            'script_path': '/test/script.m',
            'matlab_exe_path': 'matlab',
            'script_parameters': {
                'script_arguments': ['-batch', '-nosplash']
            },
            'output_path': '/test/output'
        }
        
        launcher = matlab_launcher.MATLABLauncher(params)
        mock_process = MagicMock()
        
        with patch('src.openscope_experimental_launcher.interfaces.matlab_interface.start_matlab_script', 
                   return_value=mock_process) as mock_start:
            process = launcher.create_process()
            
            assert process == mock_process
            mock_start.assert_called_once()
            
            # Check that correct arguments were passed
            call_args = mock_start.call_args
            assert call_args[0][0] == '/test/script.m'  # script_path
            assert call_args[0][1] == 'matlab'  # matlab_exe_path
            assert call_args[1]['arguments'] == ['-batch', '-nosplash']
            assert call_args[1]['output_path'] == '/test/output'

    def test_create_process_minimal_params(self):
        """Test process creation with minimal parameters."""
        params = {
            'script_path': '/test/script.m'
        }
        
        launcher = matlab_launcher.MATLABLauncher(params)
        mock_process = MagicMock()
        
        with patch('src.openscope_experimental_launcher.interfaces.matlab_interface.start_matlab_script', 
                   return_value=mock_process) as mock_start:
            process = launcher.create_process()
            
            assert process == mock_process
            mock_start.assert_called_once()
            
            # Check that correct arguments were passed
            call_args = mock_start.call_args
            assert call_args[0][0] == '/test/script.m'  # script_path

    def test_create_process_missing_script_path(self):
        """Test process creation with missing script path."""
        params = {}
        
        launcher = matlab_launcher.MATLABLauncher(params)
        
        with pytest.raises(KeyError):
            launcher.create_process()

    def test_create_process_interface_error(self):
        """Test process creation with interface error."""
        params = {
            'script_path': '/test/script.m'
        }
        
        launcher = matlab_launcher.MATLABLauncher(params)
        
        with patch('src.openscope_experimental_launcher.interfaces.matlab_interface.start_matlab_script', 
                   side_effect=Exception("Interface error")):
            with pytest.raises(Exception):
                launcher.create_process()

    def test_create_process_with_default_executable(self):
        """Test process creation with default MATLAB executable."""
        params = {
            'script_path': '/test/script.m',
            'script_parameters': {}
        }
        
        launcher = matlab_launcher.MATLABLauncher(params)
        mock_process = MagicMock()
        
        with patch('src.openscope_experimental_launcher.interfaces.matlab_interface.start_matlab_script', 
                   return_value=mock_process) as mock_start:
            process = launcher.create_process()
            
            assert process == mock_process
            mock_start.assert_called_once()
            
            # Check that default matlab executable was used
            call_args = mock_start.call_args
            assert call_args[0][1] == 'matlab'

    def test_create_process_with_custom_executable(self):
        """Test process creation with custom MATLAB executable."""
        params = {
            'script_path': '/test/script.m',
            'matlab_exe_path': '/usr/local/bin/matlab'
        }
        
        launcher = matlab_launcher.MATLABLauncher(params)
        mock_process = MagicMock()
        
        with patch('src.openscope_experimental_launcher.interfaces.matlab_interface.start_matlab_script', 
                   return_value=mock_process) as mock_start:
            process = launcher.create_process()
            
            assert process == mock_process
            mock_start.assert_called_once()
            
            # Check that custom executable was used
            call_args = mock_start.call_args
            assert call_args[0][1] == '/usr/local/bin/matlab'

    def test_create_process_with_arguments(self):
        """Test process creation with custom arguments."""
        params = {
            'script_path': '/test/script.m',
            'script_parameters': {
                'script_arguments': ['-batch', '-nosplash', '-nodesktop']
            }
        }
        
        launcher = matlab_launcher.MATLABLauncher(params)
        mock_process = MagicMock()
        
        with patch('src.openscope_experimental_launcher.interfaces.matlab_interface.start_matlab_script', 
                   return_value=mock_process) as mock_start:
            process = launcher.create_process()
            
            assert process == mock_process
            mock_start.assert_called_once()
            
            # Check that arguments were passed correctly
            call_args = mock_start.call_args
            assert call_args[1]['arguments'] == ['-batch', '-nosplash', '-nodesktop']

    def test_create_process_without_arguments(self):
        """Test process creation without custom arguments."""
        params = {
            'script_path': '/test/script.m',
            'script_parameters': {}
        }
        
        launcher = matlab_launcher.MATLABLauncher(params)
        mock_process = MagicMock()
        
        with patch('src.openscope_experimental_launcher.interfaces.matlab_interface.start_matlab_script', 
                   return_value=mock_process) as mock_start:
            process = launcher.create_process()
            
            assert process == mock_process
            mock_start.assert_called_once()
            
            # Check that no arguments were passed
            call_args = mock_start.call_args
            assert 'arguments' not in call_args[1] or call_args[1]['arguments'] is None
