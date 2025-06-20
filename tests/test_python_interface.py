"""
Tests for Python interface module.
"""

import pytest
from unittest.mock import Mock, patch

from src.openscope_experimental_launcher.interfaces import python_interface


class TestPythonInterface:
    """Test class for Python interface functionality."""

    def test_setup_python_environment_success(self):
        """Test successful Python environment setup."""
        params = {'python_exe_path': 'python'}
        
        with patch.object(python_interface, 'check_installation', return_value=True):
            result = python_interface.setup_python_environment(params)
            assert result is True

    def test_check_installation_success(self):
        """Test successful Python installation check."""
        mock_result = Mock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result):
            result = python_interface.check_installation('python')
            assert result is True

    def test_check_installation_failure(self):
        """Test Python installation check failure."""
        mock_result = Mock()
        mock_result.returncode = 1
        
        with patch('subprocess.run', return_value=mock_result):
            result = python_interface.check_installation('python')
            assert result is False

    def test_construct_python_arguments_basic(self):
        """Test basic Python argument construction."""
        params = {}
        args = python_interface.construct_python_arguments(params)
        assert isinstance(args, list)

    def test_construct_python_arguments_with_python_args(self):
        """Test Python argument construction with Python-specific arguments."""
        params = {'python_arguments': ['-O', '-v']}
        args = python_interface.construct_python_arguments(params)
        
        assert '-O' in args
        assert '-v' in args

    def test_start_python_script_file_not_found(self):
        """Test Python script startup with missing file."""
        with patch('os.path.exists', return_value=False):
            with pytest.raises(FileNotFoundError):
                python_interface.start_python_script('nonexistent.py')
