"""
Unit tests for the GitManager utility class.
"""

import os
import pytest
import subprocess
from unittest.mock import Mock, patch, call
from openscope_experimental_launcher.utils.git_manager import GitManager


class TestGitManager:
    """Test cases for GitManager class."""

    def test_init_git_available(self, mock_git_available):
        """Test GitManager initialization when Git is available."""
        git_manager = GitManager()
        assert git_manager.git_available is True

    @patch('subprocess.check_output')
    def test_init_git_not_available(self, mock_check_output):
        """Test GitManager initialization when Git is not available."""
        mock_check_output.side_effect = OSError("Git not found")
        
        git_manager = GitManager()
        assert git_manager.git_available is False

    def test_get_repo_name_from_url_https(self):
        """Test repository name extraction from HTTPS URL."""
        git_manager = GitManager()
        
        url = "https://github.com/test/repo.git"
        name = git_manager._get_repo_name_from_url(url)
        assert name == "repo"
        
        url = "https://github.com/test/repo"
        name = git_manager._get_repo_name_from_url(url)
        assert name == "repo"

    def test_setup_repository_no_config(self):
        """Test repository setup when no configuration provided."""
        git_manager = GitManager()
        
        params = {}
        result = git_manager.setup_repository(params)
        
        assert result is True

    def test_setup_repository_git_not_available(self):
        """Test repository setup when Git is not available."""
        with patch('subprocess.check_output', side_effect=OSError()):
            git_manager = GitManager()
            
            params = {
                'repository_url': 'https://github.com/test/repo.git',
                'local_repository_path': '/tmp/test'
            }
            result = git_manager.setup_repository(params)
            
            assert result is False

    @patch('os.path.exists')
    @patch('subprocess.check_call')
    def test_clone_repository_success(self, mock_check_call, mock_exists, mock_git_available):
        """Test successful repository cloning."""
        mock_exists.return_value = True
        git_manager = GitManager()
        
        result = git_manager._clone_repository(
            "https://github.com/test/repo.git", 
            "/tmp/test/repo"
        )
        
        assert result is True
        mock_check_call.assert_called_once()

    @patch('subprocess.check_call')
    def test_clone_repository_failure(self, mock_check_call, mock_git_available):
        """Test repository cloning failure."""
        mock_check_call.side_effect = subprocess.CalledProcessError(1, 'git')
        git_manager = GitManager()
        
        result = git_manager._clone_repository(
            "https://github.com/test/repo.git", 
            "/tmp/test/repo"
        )
        
        assert result is False

    @patch('os.getcwd')
    @patch('os.chdir')
    @patch('subprocess.check_output')
    def test_get_current_commit_hash(self, mock_check_output, mock_chdir, mock_getcwd, mock_git_available):
        """Test getting current commit hash."""
        mock_getcwd.return_value = "/original"
        mock_check_output.return_value = b"abc123def456\n"
        
        git_manager = GitManager()
        commit_hash = git_manager._get_current_commit_hash("/repo/path")
        
        assert commit_hash == "abc123def456"
        mock_chdir.assert_has_calls([call("/repo/path"), call("/original")])

    def test_get_repository_path(self, mock_git_available):
        """Test getting repository path."""
        git_manager = GitManager()
        
        params = {
            'repository_url': 'https://github.com/test/repo.git',
            'local_repository_path': '/tmp/test'
        }
        
        path = git_manager.get_repository_path(params)
        # Use os.path.join for cross-platform compatibility
        expected_path = os.path.join("/tmp/test", "repo")
        assert path == expected_path

    def test_get_repository_path_no_config(self, mock_git_available):
        """Test getting repository path with no configuration."""
        git_manager = GitManager()
        
        params = {}
        path = git_manager.get_repository_path(params)
        assert path is None

    @patch('os.path.exists')
    @patch('shutil.rmtree')
    def test_force_remove_directory_success(self, mock_rmtree, mock_exists, mock_git_available):
        """Test successful directory removal."""
        mock_exists.return_value = True
        git_manager = GitManager()
        
        result = git_manager._force_remove_directory("/test/path")
        
        assert result is True
        mock_rmtree.assert_called_once()

    @patch('shutil.rmtree')
    def test_force_remove_directory_failure(self, mock_rmtree, mock_git_available):
        """Test directory removal failure."""
        mock_rmtree.side_effect = Exception("Remove failed")
        git_manager = GitManager()
        
        result = git_manager._force_remove_directory("/test/path")
        
        assert result is False