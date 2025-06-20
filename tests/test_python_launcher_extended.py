"""
Tests for Python launcher module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.openscope_experimental_launcher.launchers import python_launcher


class TestPythonLauncher:
    """Test cases for Python launcher."""

    def test_init_default_params(self):
        """Test PythonLauncher initialization with default parameters."""
        launcher = python_launcher.PythonLauncher()
        
        assert launcher is not None
        assert hasattr(launcher, 'logger')

    def test_init_with_params(self):
        """Test PythonLauncher initialization with parameters."""
        params = {
            'python_executable': '/usr/bin/python3',
            'script_path': '/test/script.py',
            'output_path': '/test/output'
        }
        
        launcher = python_launcher.PythonLauncher(params)
        
        assert launcher is not None
        assert hasattr(launcher, 'logger')

    def test_create_process_success(self):
        """Test successful process creation."""
        params = {
            'script_path': '/test/script.py',
            'python_executable': 'python',
            'script_parameters': {
                'script_arguments': ['-u', '--verbose'],
                'environment_variables': {'PYTHONPATH': '/test/path'}
            },
            'output_path': '/test/output'
        }
        
        launcher = python_launcher.PythonLauncher(params)
        mock_process = MagicMock()
        
        with patch('src.openscope_experimental_launcher.interfaces.python_interface.start_python_script', 
                   return_value=mock_process) as mock_start:
            process = launcher.create_process()
            
            assert process == mock_process
            mock_start.assert_called_once()
            
            # Check that correct arguments were passed
            call_args = mock_start.call_args
            assert call_args[0][0] == '/test/script.py'  # script_path
            assert call_args[1]['python_executable'] == 'python'
            assert call_args[1]['arguments'] == ['-u', '--verbose']
            assert call_args[1]['environment'] == {'PYTHONPATH': '/test/path'}
            assert call_args[1]['output_path'] == '/test/output'

    def test_create_process_minimal_params(self):
        """Test process creation with minimal parameters."""
        params = {
            'script_path': '/test/script.py'
        }
        
        launcher = python_launcher.PythonLauncher(params)
        mock_process = MagicMock()
        
        with patch('src.openscope_experimental_launcher.interfaces.python_interface.start_python_script', 
                   return_value=mock_process) as mock_start:
            process = launcher.create_process()
            
            assert process == mock_process
            mock_start.assert_called_once()
            
            # Check that correct arguments were passed
            call_args = mock_start.call_args
            assert call_args[0][0] == '/test/script.py'  # script_path

    def test_create_process_missing_script_path(self):
        """Test process creation with missing script path."""
        params = {}
        
        launcher = python_launcher.PythonLauncher(params)
        
        with pytest.raises(KeyError):
            launcher.create_process()

    def test_create_process_interface_error(self):
        """Test process creation with interface error."""
        params = {
            'script_path': '/test/script.py'
        }
        
        launcher = python_launcher.PythonLauncher(params)
        
        with patch('src.openscope_experimental_launcher.interfaces.python_interface.start_python_script', 
                   side_effect=Exception("Interface error")):
            with pytest.raises(Exception):
                launcher.create_process()

    def test_create_process_with_default_executable(self):
        """Test process creation with default Python executable."""
        params = {
            'script_path': '/test/script.py',
            'script_parameters': {}
        }
        
        launcher = python_launcher.PythonLauncher(params)
        mock_process = MagicMock()
        
        with patch('src.openscope_experimental_launcher.interfaces.python_interface.start_python_script', 
                   return_value=mock_process) as mock_start:
            process = launcher.create_process()
            
            assert process == mock_process
            mock_start.assert_called_once()
            
            # Check that default python executable was used
            call_args = mock_start.call_args
            assert call_args[1]['python_executable'] == 'python'

    def test_create_process_with_custom_executable(self):
        """Test process creation with custom Python executable."""
        params = {
            'script_path': '/test/script.py',
            'python_executable': '/usr/bin/python3.9'
        }
        
        launcher = python_launcher.PythonLauncher(params)
        mock_process = MagicMock()
        
        with patch('src.openscope_experimental_launcher.interfaces.python_interface.start_python_script', 
                   return_value=mock_process) as mock_start:
            process = launcher.create_process()
            
            assert process == mock_process
            mock_start.assert_called_once()
            
            # Check that custom executable was used
            call_args = mock_start.call_args
            assert call_args[1]['python_executable'] == '/usr/bin/python3.9'
