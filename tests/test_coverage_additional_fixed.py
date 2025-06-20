"""
Additional coverage tests to reach 65% threshold.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from src.openscope_experimental_launcher.utils import git_manager
from src.openscope_experimental_launcher.interfaces import bonsai_interface
from src.openscope_experimental_launcher.utils import process_monitor


class TestCoverageBoost:
    """Tests to increase coverage to 65%."""
    
    def test_git_manager_get_repo_name(self):
        """Test repo name extraction."""
        name = git_manager._get_repo_name_from_url('https://github.com/test/repo.git')
        assert name == 'repo'
    
    def test_git_manager_check_git_available(self):
        """Test git availability check."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            result = git_manager._check_git_available()
            assert result is True
    
    def test_git_manager_force_remove(self):
        """Test force remove directory."""
        with patch('shutil.rmtree'):
            result = git_manager._force_remove_directory('/test')
            assert result is True
            
    def test_bonsai_interface_property_args_empty(self):
        """Test Bonsai property arguments with empty params."""
        params = {}
        args = bonsai_interface.create_bonsai_property_arguments(params)
        assert args == []
        
    def test_bonsai_interface_property_args_with_script_params(self):
        """Test Bonsai property arguments with script_parameters."""
        params = {'script_parameters': {'test': 'value', 'test2': 'value2'}}
        args = bonsai_interface.create_bonsai_property_arguments(params)
        assert '-p' in args
        assert 'test=value' in args
        assert 'test2=value2' in args
        
    def test_bonsai_interface_workflow_args_empty(self):
        """Test Bonsai workflow arguments with empty params."""
        params = {}
        args = bonsai_interface.construct_workflow_arguments(params)
        assert isinstance(args, list)
        assert args == []
        
    def test_bonsai_interface_workflow_args_with_script_args(self):
        """Test Bonsai workflow arguments with script arguments."""
        params = {'script_arguments': ['--verbose', '--debug']}
        args = bonsai_interface.construct_workflow_arguments(params)
        assert '--verbose' in args
        assert '--debug' in args
        
    def test_bonsai_interface_install_script_not_found(self):
        """Test Bonsai installation with missing script."""
        result = bonsai_interface.install_bonsai('nonexistent_script.bat')
        assert result is False
        
    def test_bonsai_interface_verify_packages_no_config(self):
        """Test package verification with missing config file."""
        with patch('os.path.exists', return_value=False):
            result = bonsai_interface.verify_packages('config.xml', '/empty/dir')
            assert result is True  # Returns True when no config file exists
            
    def test_bonsai_interface_get_installed_packages_no_dir(self):
        """Test getting installed packages from nonexistent directory."""
        with patch('os.path.exists', return_value=False):
            result = bonsai_interface.get_installed_packages('/empty/dir')
            assert result == {}
            
    def test_bonsai_interface_get_installed_packages_with_files(self):
        """Test getting installed packages with package files (not directories)."""
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir', return_value=['Package1.dll', 'Package2.dll']), \
             patch('os.path.isdir', return_value=False):
            result = bonsai_interface.get_installed_packages('/test/dir')
            # Should return empty dict as files are not directories
            assert result == {}
            
    def test_bonsai_interface_versions_match(self):
        """Test version matching logic."""
        assert bonsai_interface._versions_match('1.0.0', '1.0.0') is True
        assert bonsai_interface._versions_match('1.0.0', '1.0.1') is False
        assert bonsai_interface._versions_match('1.0', '1.0.0') is True
        
    def test_bonsai_interface_normalize_version(self):
        """Test version normalization."""
        assert bonsai_interface._normalize_version('1.0.0') == '1'
        assert bonsai_interface._normalize_version('1.2.0') == '1.2'
        assert bonsai_interface._normalize_version('1.2.3') == '1.2.3'
        
    def test_process_monitor_memory_info_none(self):
        """Test process memory info with None process."""
        result = process_monitor.get_process_memory_info(None)
        assert result == {}
        
    def test_process_monitor_memory_info_with_process(self):
        """Test process memory info with valid process."""
        mock_process = Mock()
        mock_process.pid = 1234
        
        mock_ps_process = Mock()
        mock_memory_info = Mock(rss=1024000, vms=2048000)
        mock_ps_process.memory_info.return_value = mock_memory_info
        
        with patch('psutil.Process', return_value=mock_ps_process):
            result = process_monitor.get_process_memory_info(mock_process)
            # The function returns the memory_info object directly
            assert result == mock_memory_info
            
    def test_process_monitor_responsive_finished(self):
        """Test process responsive check with finished process."""
        mock_process = Mock()
        mock_process.poll.return_value = 0  # Process has finished
        result = process_monitor.is_process_responsive(mock_process)
        assert result is False  # Finished process is not responsive
        
    def test_process_monitor_responsive_with_exception(self):
        """Test process responsive check with exception."""
        mock_process = Mock()
        mock_process.poll.side_effect = Exception("Mock error")
        result = process_monitor.is_process_responsive(mock_process)
        assert result is True  # Returns True on exception
        
    def test_git_manager_current_commit_hash_error(self):
        """Test getting current commit hash with error."""
        with patch('subprocess.run', side_effect=Exception("Git error")):
            result = git_manager._get_current_commit_hash('/test/path')
            assert result is None
            
    def test_git_manager_remote_commit_hash_success(self):
        """Test getting remote commit hash with proper path mocking."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = 'abc123def456\n'
        
        with patch('subprocess.run', return_value=mock_result), \
             patch('os.path.exists', return_value=True):
            result = git_manager._get_remote_commit_hash('/test/path')
            assert result == 'abc123def456'
            
    def test_git_manager_is_on_target_commit_true(self):
        """Test checking if on target commit - true case."""
        with patch.object(git_manager, '_get_current_commit_hash', return_value='abc123'):
            result = git_manager._is_on_target_commit('/test/path', 'abc123')
            assert result is True
            
    def test_git_manager_is_on_target_commit_false(self):
        """Test checking if on target commit - false case."""
        with patch.object(git_manager, '_get_current_commit_hash', return_value='def456'):
            result = git_manager._is_on_target_commit('/test/path', 'abc123')
            assert result is False
            
    def test_git_manager_clone_repository_success(self):
        """Test successful repository cloning."""
        mock_result = Mock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result), \
             patch('os.path.exists', return_value=False):
            result = git_manager._clone_repository('https://test.git', '/test/path')
            assert result is True
            
    def test_git_manager_clone_repository_exists(self):
        """Test repository cloning when directory exists."""
        with patch('os.path.exists', return_value=True):
            result = git_manager._clone_repository('https://test.git', '/test/path')
            assert result is False
            
    def test_git_manager_checkout_commit_success(self):
        """Test successful commit checkout."""
        mock_result = Mock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result), \
             patch('os.path.exists', return_value=True):
            result = git_manager._checkout_commit('/test/path', 'abc123')
            assert result is True
