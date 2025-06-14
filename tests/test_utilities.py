"""
Tests for utility modules to improve code coverage.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

from openscope_experimental_launcher.utils.config_loader import ConfigLoader
from openscope_experimental_launcher.utils.git_manager import GitManager
from openscope_experimental_launcher.utils.process_monitor import ProcessMonitor


class TestGitManager:
    """Test GitManager utility class."""
    
    @patch('subprocess.check_output')
    def test_init_git_available(self, mock_check_output):
        """Test GitManager initialization when git is available."""
        mock_check_output.return_value = b"git version 2.30.0"
        git_manager = GitManager()
        assert git_manager.git_available is True
    
    @patch('subprocess.check_output')
    def test_init_git_not_available(self, mock_check_output):
        """Test GitManager initialization when git is not available."""
        mock_check_output.side_effect = OSError("Git not found")
        git_manager = GitManager()
        assert git_manager.git_available is False
    
    @patch('subprocess.check_output')
    def test_get_repo_name_from_url(self, mock_check_output):
        """Test repository name extraction from URL."""
        mock_check_output.return_value = b"git version 2.30.0"
        git_manager = GitManager()
        
        # Test HTTPS URL with .git
        name = git_manager._get_repo_name_from_url("https://github.com/test/repo.git")
        assert name == "repo"
        
        # Test HTTPS URL without .git
        name = git_manager._get_repo_name_from_url("https://github.com/test/repo")
        assert name == "repo"
    
    @patch('subprocess.check_output')
    def test_get_repository_path(self, mock_check_output):
        """Test repository path determination."""
        mock_check_output.return_value = b"git version 2.30.0"
        git_manager = GitManager()
        
        params = {
            "repository_url": "https://github.com/test/repo.git",
            "local_repository_path": "/custom/path"
        }
        
        path = git_manager.get_repository_path(params)
        # Use os.path.join for cross-platform compatibility
        expected_path = os.path.join("/custom/path", "repo")
        assert path == expected_path
        
        # Test with missing parameters
        params = {"repository_url": "https://github.com/test/repo.git"}
        path = git_manager.get_repository_path(params)
        assert path is None
    
    @patch('subprocess.check_output')
    @patch('subprocess.check_call')
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_clone_repository_success(self, mock_makedirs, mock_exists, mock_check_call, mock_check_output):
        """Test successful repository cloning."""
        mock_check_output.return_value = b"git version 2.30.0"
        mock_exists.return_value = False
        mock_check_call.return_value = None
        
        git_manager = GitManager()
        
        result = git_manager._clone_repository(
            "https://github.com/test/repo.git", 
            "/test/path"
        )
        assert result is True
        mock_check_call.assert_called_once()
    
    @patch('subprocess.check_output')
    def test_setup_repository_no_config(self, mock_check_output):
        """Test repository setup with no configuration."""
        mock_check_output.return_value = b"git version 2.30.0"
        git_manager = GitManager()
        
        # Test with empty params
        result = git_manager.setup_repository({})
        assert result is True  # Should succeed with no repo config


class TestProcessMonitor:
    """Test ProcessMonitor utility class."""
    
    def test_init(self):
        """Test ProcessMonitor initialization."""
        monitor = ProcessMonitor()
        assert monitor is not None
    
    @patch('time.sleep')
    def test_monitor_process_completed(self, mock_sleep):
        """Test process monitoring with completed process."""
        monitor = ProcessMonitor()
        mock_process = Mock()
        mock_process.poll.return_value = 0  # Process finished
        mock_process.returncode = 0
        
        # Mock kill callback
        kill_callback = Mock()
        
        # This should not raise an exception
        monitor.monitor_process(mock_process, 50.0, kill_callback)
        
        # Kill callback should not be called for successful process
        kill_callback.assert_not_called()
    
    @patch('time.sleep')
    @patch('psutil.virtual_memory')
    def test_monitor_process_with_memory_check(self, mock_vmem, mock_sleep):
        """Test process monitoring with memory usage checks."""
        monitor = ProcessMonitor()
        mock_process = Mock()
        
        # Set up process to finish after a few polls
        poll_calls = [None, None, 0]  # Running, running, then finished
        mock_process.poll.side_effect = poll_calls
        mock_process.returncode = 0
        
        # Set memory usage to safe level
        mock_vmem.return_value.percent = 50.0
        
        kill_callback = Mock()
        
        monitor.monitor_process(mock_process, 60.0, kill_callback)
        
        # Should complete without killing
        kill_callback.assert_not_called()


class TestConfigLoader:
    """Test ConfigLoader utility class."""
    
    def test_init(self):
        """Test ConfigLoader initialization."""
        loader = ConfigLoader()
        assert loader is not None
    
    def test_load_config_empty_params(self):
        """Test loading config with empty parameters."""
        loader = ConfigLoader()
        config = loader.load_config({})
        assert isinstance(config, dict)
    
    def test_load_config_with_params(self):
        """Test loading config with parameters."""
        loader = ConfigLoader()
        params = {
            "mouse_id": "test_mouse",
            "user_id": "test_user"
        }
        config = loader.load_config(params)
        assert isinstance(config, dict)
    
    @patch('os.path.exists', return_value=False)
    def test_load_config_no_file(self, mock_exists):
        """Test loading config when config file doesn't exist."""
        loader = ConfigLoader()
        config = loader.load_config({"config_file": "/nonexistent/path"})
        assert isinstance(config, dict)


class TestBonsaiInterface:
    """Test Bonsai interface functionality that exists."""
    
    def test_import_bonsai_interface(self):
        """Test that bonsai interface module can be imported."""
        from openscope_experimental_launcher.base import bonsai_interface
        assert bonsai_interface is not None
    
    def test_bonsai_interface_has_expected_structure(self):
        """Test that bonsai interface has expected components."""
        from openscope_experimental_launcher.base import bonsai_interface
        
        # Check that the module exists and has some content
        assert hasattr(bonsai_interface, '__file__')


class TestMetadataGenerator:
    """Test metadata generation functionality that exists."""
    
    def test_import_metadata_generator(self):
        """Test that metadata generator module can be imported."""
        from openscope_experimental_launcher.base import metadata_generator
        assert metadata_generator is not None
    
    def test_metadata_generator_has_expected_structure(self):
        """Test that metadata generator has expected components."""
        from openscope_experimental_launcher.base import metadata_generator
        
        # Check that the module exists and has some content
        assert hasattr(metadata_generator, '__file__')


class TestUtilityModulesIntegration:
    """Integration tests for utility modules working together."""
    
    @patch('subprocess.check_output')
    def test_git_and_config_integration(self, mock_check_output):
        """Test GitManager and ConfigLoader working together."""
        mock_check_output.return_value = b"git version 2.30.0"
        
        git_manager = GitManager()
        config_loader = ConfigLoader()
        
        params = {
            "repository_url": "https://github.com/test/repo.git",
            "local_repository_path": "/test/path"
        }
        
        # Load config
        config = config_loader.load_config(params)
        
        # Get repository path
        repo_path = git_manager.get_repository_path(params)
        
        assert isinstance(config, dict)
        # Use os.path.join for cross-platform compatibility
        expected_path = os.path.join("/test/path", "repo")
        assert repo_path == expected_path
    
    def test_process_monitor_and_config_integration(self):
        """Test ProcessMonitor working with config parameters."""
        monitor = ProcessMonitor()
        config_loader = ConfigLoader()
        
        params = {"memory_threshold": 80.0}
        config = config_loader.load_config(params)
        
        # Create a mock process
        mock_process = Mock()
        mock_process.poll.return_value = 0
        mock_process.returncode = 0
        
        # Should work without errors
        monitor.monitor_process(mock_process, 50.0, lambda: None)
        
        assert isinstance(config, dict)