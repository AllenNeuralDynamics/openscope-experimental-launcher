"""
Final coverage boost tests to reach 65% threshold with correct API usage.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import subprocess

from src.openscope_experimental_launcher.utils import git_manager
from src.openscope_experimental_launcher.interfaces import bonsai_interface, python_interface
from src.openscope_experimental_launcher.utils import process_monitor, session_builder
from src.openscope_experimental_launcher.launchers import python_launcher, matlab_launcher


class TestFinalCoverageBoost:
    """Tests with correct API usage to reach 65% coverage."""
    
    def test_python_interface_construct_arguments_empty(self):
        """Test Python argument construction with empty params."""
        params = {}
        args = python_interface.construct_python_arguments(params)
        assert args == []
        
    def test_python_interface_construct_arguments_with_args(self):
        """Test Python argument construction with script arguments."""
        params = {
            'python_arguments': ['--verbose'],
            'script_arguments': ['--input', 'file.txt']
        }
        args = python_interface.construct_python_arguments(params)
        assert '--verbose' in args
        assert '--input' in args
        assert 'file.txt' in args
        
    def test_python_interface_check_installation_default(self):
        """Test Python installation check with default executable."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            result = python_interface.check_installation()
            assert result is True
            
    def test_python_interface_check_installation_custom(self):
        """Test Python installation check with custom executable."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            result = python_interface.check_installation('/custom/python')
            assert result is True
            
    def test_python_interface_check_installation_failed(self):
        """Test Python installation check with failure."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("Python not found")
            result = python_interface.check_installation()
            assert result is False
            
    def test_python_interface_activate_venv_missing(self):
        """Test virtual environment activation with missing venv."""
        with patch('os.path.exists', return_value=False):
            result = python_interface.activate_virtual_environment('/nonexistent/venv')
            assert result is False
            
    def test_python_interface_setup_environment_no_venv(self):
        """Test Python environment setup without venv."""
        params = {'python_exe_path': 'python'}
        with patch('src.openscope_experimental_launcher.interfaces.python_interface.check_installation', return_value=True):
            result = python_interface.setup_python_environment(params)
            assert result is True
            
    def test_python_interface_setup_environment_with_venv(self):
        """Test Python environment setup with venv."""
        params = {
            'python_exe_path': 'python',
            'python_venv_path': '/test/venv'
        }
        with patch('src.openscope_experimental_launcher.interfaces.python_interface.check_installation', return_value=True), \
             patch('src.openscope_experimental_launcher.interfaces.python_interface.activate_virtual_environment', return_value=True):
            result = python_interface.setup_python_environment(params)
            assert result is True
            
    def test_python_interface_setup_environment_failed(self):
        """Test Python environment setup failure."""
        params = {'python_exe_path': 'python'}
        with patch('src.openscope_experimental_launcher.interfaces.python_interface.check_installation', return_value=False):
            result = python_interface.setup_python_environment(params)
            assert result is False
            
    def test_python_launcher_create_process_no_params(self):
        """Test Python launcher process creation without parameters."""
        with patch('src.openscope_experimental_launcher.interfaces.python_interface.setup_python_environment', return_value=True), \
             patch('src.openscope_experimental_launcher.interfaces.python_interface.start_python_script') as mock_start, \
             patch('os.path.exists', return_value=True):
            
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            launcher = python_launcher.PythonLauncher()
            launcher.params = {'script_path': 'test.py'}
            
            result = launcher.create_process()
            assert result == mock_process
            
    def test_matlab_launcher_create_process_no_params(self):
        """Test Matlab launcher process creation without parameters."""
        with patch('src.openscope_experimental_launcher.interfaces.matlab_interface.setup_matlab_environment', return_value=True), \
             patch('src.openscope_experimental_launcher.interfaces.matlab_interface.start_matlab_script') as mock_start, \
             patch('os.path.exists', return_value=True):
            
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            launcher = matlab_launcher.MatlabLauncher()
            launcher.params = {'script_path': 'test.m'}
            
            result = launcher.create_process()
            assert result == mock_process
            
    def test_process_monitor_memory_info_safe(self):
        """Test process memory info with safe handling."""
        mock_process = Mock()
        mock_process.pid = 1234
        
        with patch('psutil.Process') as mock_ps:
            mock_ps_instance = Mock()
            mock_ps.return_value = mock_ps_instance
            
            # Mock the memory info
            mock_memory_info = Mock()
            mock_memory_info.rss = 1024000
            mock_memory_info.vms = 2048000
            mock_ps_instance.memory_info.return_value = mock_memory_info
            
            # Mock system memory
            mock_virtual_memory = Mock()
            mock_virtual_memory.total = 8000000000
            mock_virtual_memory.available = 4000000000
            mock_virtual_memory.percent = 50.0
            
            with patch('psutil.virtual_memory', return_value=mock_virtual_memory):
                result = process_monitor.get_process_memory_info(mock_process)
                
                # Verify result structure
                assert isinstance(result, dict)
                assert 'rss' in result
                assert 'total' in result
                assert 'available' in result
                
    def test_process_monitor_is_responsive_running(self):
        """Test process responsiveness check with running process."""
        mock_process = Mock()
        mock_process.poll.return_value = None  # Still running
        
        with patch('time.time', side_effect=[100, 105]):  # 5 second difference
            result = process_monitor.is_process_responsive(mock_process)
            assert result is True
            
    def test_git_manager_check_git_available_success(self):
        """Test git availability check success."""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            result = git_manager._check_git_available()
            assert result is True
            
    def test_git_manager_check_git_available_failure(self):
        """Test git availability check failure."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("git not found")
            
            result = git_manager._check_git_available()
            assert result is False
            
    def test_git_manager_get_repo_name_various_formats(self):
        """Test repository name extraction from various URL formats."""
        # Standard GitHub URL
        name = git_manager._get_repo_name_from_url('https://github.com/user/repo.git')
        assert name == 'repo'
        
        # URL without .git
        name = git_manager._get_repo_name_from_url('https://github.com/user/repo')
        assert name == 'repo'
        
        # SSH URL
        name = git_manager._get_repo_name_from_url('git@github.com:user/repo.git')
        assert name == 'repo'
        
    def test_bonsai_interface_create_property_arguments_comprehensive(self):
        """Test Bonsai property arguments creation with comprehensive params."""
        params = {
            'script_parameters': {
                'param1': 'value1',
                'param2': 'value2',
                'param3': 'value3'
            }
        }
        args = bonsai_interface.create_bonsai_property_arguments(params)
        
        assert '-p' in args
        assert 'param1=value1' in args
        assert 'param2=value2' in args
        assert 'param3=value3' in args
        
    def test_bonsai_interface_normalize_version_various_formats(self):
        """Test version normalization with various formats."""
        # Test standard version
        result = bonsai_interface._normalize_version('1.2.3')
        assert result == '1.2.3'
        
        # Test trailing zero removal
        result = bonsai_interface._normalize_version('1.2.0')
        assert result == '1.2'
        
        # Test single digit
        result = bonsai_interface._normalize_version('1.0.0')
        assert result == '1'
        
    def test_bonsai_interface_versions_match_comprehensive(self):
        """Test version matching with comprehensive scenarios."""
        # Exact matches
        assert bonsai_interface._versions_match('1.2.3', '1.2.3') is True
        
        # Normalized matches
        assert bonsai_interface._versions_match('1.2', '1.2.0') is True
        assert bonsai_interface._versions_match('1.2.0', '1.2') is True
        
        # Mismatches
        assert bonsai_interface._versions_match('1.2.3', '1.2.4') is False
        assert bonsai_interface._versions_match('1.2', '1.3') is False
        
    def test_session_builder_get_additional_script_parameters_filtering(self):
        """Test additional script parameters filtering."""
        params = {
            'script_parameters': {'param1': 'value1'},
            'extra_param': 'extra_value',
            'another_param': 'another_value'
        }
        
        result = session_builder.get_additional_script_parameters(params, 'test_rig')
        
        # Should be empty dict if no additional params beyond script_parameters
        assert isinstance(result, dict)
        
    def test_git_manager_force_remove_directory_success(self):
        """Test force remove directory success."""
        with patch('shutil.rmtree') as mock_rmtree:
            result = git_manager._force_remove_directory('/test/path')
            assert result is True
            # The function calls rmtree with onerror parameter
            mock_rmtree.assert_called_once()
            call_args = mock_rmtree.call_args
            assert call_args[0][0] == '/test/path'
            assert 'onerror' in call_args[1]
            
    def test_git_manager_force_remove_directory_failure(self):
        """Test force remove directory failure."""
        with patch('shutil.rmtree', side_effect=OSError("Permission denied")):
            result = git_manager._force_remove_directory('/test/path')
            assert result is False
            
    def test_bonsai_interface_verify_packages_empty_paths(self):
        """Test package verification with empty paths."""
        result = bonsai_interface.verify_packages('', '')
        assert result is True
        
    def test_bonsai_interface_get_installed_packages_empty_path(self):
        """Test getting installed packages with empty path."""
        result = bonsai_interface.get_installed_packages('')
        assert result == {}
