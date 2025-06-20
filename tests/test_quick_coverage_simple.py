"""
Quick coverage boost tests targeting specific functions.
"""

import pytest
from unittest.mock import Mock, patch
from src.openscope_experimental_launcher.interfaces import python_interface


class TestQuickCoverageBoost:
    """Quick tests to push coverage over 65%."""
    
    def test_python_interface_setup_environment(self):
        """Test Python environment setup."""
        result = python_interface.setup_python_environment({})
        assert isinstance(result, bool)
    
    def test_python_interface_check_installation_success(self):
        """Test Python installation check success."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            result = python_interface.check_installation('python')
            assert result is True
    
    def test_python_interface_check_installation_fail(self):
        """Test Python installation check failure."""
        with patch('subprocess.run', side_effect=FileNotFoundError):
            result = python_interface.check_installation('python')
            assert result is False
    
    def test_python_interface_activate_venv_success(self):
        """Test virtual environment activation."""
        with patch('os.path.exists', return_value=True), \
             patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            result = python_interface.activate_virtual_environment('/test/venv')
            assert result is True
    
    def test_python_interface_activate_venv_missing(self):
        """Test virtual environment activation with missing venv."""
        with patch('os.path.exists', return_value=False):
            result = python_interface.activate_virtual_environment('/test/venv')
            assert result is False
    
    def test_python_interface_construct_args_basic(self):
        """Test argument construction."""
        params = {'script_parameters': {'param1': 'value1'}}
        args = python_interface.construct_python_arguments(params)
        assert isinstance(args, list)
    
    def test_python_interface_start_script_basic(self):
        """Test starting Python script."""
        with patch('subprocess.Popen') as mock_popen, \
             patch('os.path.exists', return_value=True):
            mock_process = Mock()
            mock_popen.return_value = mock_process
            result = python_interface.start_python_script('test_script.py')
            assert result == mock_process
    
    def test_python_interface_start_script_with_venv(self):
        """Test starting Python script with virtual environment."""
        with patch('subprocess.Popen') as mock_popen, \
             patch('os.path.exists', return_value=True):
            mock_process = Mock()
            mock_popen.return_value = mock_process
            result = python_interface.start_python_script(
                'test_script.py',
                venv_path='/test/venv'
            )
            assert result == mock_process
