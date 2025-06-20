"""
Tests for utility modules (updated for functional approach).
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil
import subprocess

from openscope_experimental_launcher.utils import config_loader
from openscope_experimental_launcher.utils import git_manager  
from openscope_experimental_launcher.utils import process_monitor


class TestGitManagerFunctions:
    """Test git_manager utility functions."""
    
    def test_get_repository_path_no_config(self):
        """Test repository path with no configuration."""
        params = {}
        result = git_manager.get_repository_path(params)
        assert result is None
    
    def test_get_repository_path_with_config(self):
        """Test repository path with configuration."""
        params = {
            'repository_url': 'https://github.com/test/repo.git',
            'local_repository_path': '/tmp/test'
        }
        result = git_manager.get_repository_path(params)
        expected = os.path.join('/tmp/test', 'repo')
        assert result == expected
    
    @patch('subprocess.check_output')
    def test_check_git_available_true(self, mock_check_output):
        """Test git availability check when git is available."""
        mock_check_output.return_value = b"git version 2.30.0"
        result = git_manager._check_git_available()
        assert result is True
    
    @patch('subprocess.check_output') 
    def test_check_git_available_false(self, mock_check_output):
        """Test git availability check when git is not available."""
        mock_check_output.side_effect = OSError("Git not found")
        result = git_manager._check_git_available()
        assert result is False
    
    @patch('openscope_experimental_launcher.utils.git_manager._check_git_available')
    def test_setup_repository_no_config(self, mock_git_check):
        """Test repository setup with no configuration."""
        mock_git_check.return_value = True
        params = {}
        result = git_manager.setup_repository(params)
        assert result is True  # Should return True when no repo config


class TestProcessMonitorFunctions:
    """Test process_monitor utility functions."""
    
    @patch('psutil.Process')
    def test_get_process_memory_info(self, mock_process_class):
        """Test process memory info retrieval."""
        # Create mock process
        mock_process = MagicMock()
        mock_process.pid = 1234
        mock_real_process = MagicMock()
        mock_real_process.memory_info.return_value = MagicMock(rss=1000, vms=2000)
        mock_real_process.memory_percent.return_value = 5.0
        mock_process_class.return_value = mock_real_process
        
        # Mock psutil.virtual_memory
        with patch('psutil.virtual_memory') as mock_vmem:
            mock_vmem.return_value = MagicMock(available=8000, total=16000)
            
            result = process_monitor.get_process_memory_info(mock_process)
            
            assert isinstance(result, dict)
            assert 'rss' in result
            assert 'vms' in result
            assert 'percent' in result
            assert 'available' in result
            assert 'total' in result
    
    @patch('psutil.Process')
    def test_is_process_responsive(self, mock_process_class):
        """Test process responsiveness check."""
        # Create mock process
        mock_process = MagicMock()
        mock_process.pid = 1234
        mock_real_process = MagicMock()
        mock_real_process.status.return_value = 'running'
        mock_process_class.return_value = mock_real_process
        
        result = process_monitor.is_process_responsive(mock_process)
        assert result is True


class TestConfigLoaderFunctions:
    """Test config_loader utility functions."""
    
    def test_load_config_default(self):
        """Test config loading with default parameters."""
        params = {}
        config = config_loader.load_config(params)
        
        # Should return a dictionary with expected sections
        assert isinstance(config, dict)
        expected_sections = ['Behavior', 'Encoder', 'Reward', 'Licksensing', 
                           'Sync', 'Stim', 'LIMS', 'SweepStim', 'Display', 'Datastream']
        for section in expected_sections:
            assert section in config
            assert isinstance(config[section], dict)
    
    def test_load_config_custom_path(self):
        """Test config loading with custom path."""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False) as f:
            f.write("""
[TestSection]
test_key = test_value
""")
            temp_config_path = f.name
        
        try:
            params = {"config_path": temp_config_path}
            config = config_loader.load_config(params)
            
            # Should still have all default sections plus any custom ones
            assert isinstance(config, dict)
            assert len(config) >= 10  # At least the default sections
            
        finally:
            os.unlink(temp_config_path)
    
    def test_get_default_config_dir(self):
        """Test default config directory function."""
        result = config_loader._get_default_config_dir()
        assert isinstance(result, str)
        assert len(result) > 0


class TestUtilityIntegration:
    """Test utilities working together (simplified version)."""
    
    def test_config_and_git_integration(self):
        """Test config_loader and git_manager working together."""
        # Test basic functionality without complex mocking
        params = {
            'repository_url': 'https://github.com/test/repo.git',
            'local_repository_path': '/tmp/test'
        }
        
        # Test git manager
        repo_path = git_manager.get_repository_path(params)
        assert repo_path is not None
        
        # Test config loader
        config = config_loader.load_config(params)
        assert isinstance(config, dict)
        assert len(config) > 0


# Keep the BonsaiInterface tests but update them for functional approach
class TestBonsaiInterface:
    """Test bonsai_interface utility functions."""
    
    def test_construct_workflow_arguments(self):
        """Test workflow argument construction."""
        from openscope_experimental_launcher.interfaces import bonsai_interface
        
        params = {
            "script_parameters": {
                "TestParam1": "value1",
                "TestParam2": 42
            }
        }
        
        args = bonsai_interface.construct_workflow_arguments(params)
        
        # Should contain -p arguments for each parameter
        assert isinstance(args, list)
        assert "-p" in args
        assert "TestParam1=value1" in args
        assert "TestParam2=42" in args
