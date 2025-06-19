"""
Unit tests for the git_manager utility functions.
"""

import os
import pytest
import subprocess
from unittest.mock import Mock, patch, call
from openscope_experimental_launcher.utils import git_manager


class TestGitManagerFunctions:
    """Test cases for git_manager functions."""

    def test_check_git_available_true(self):
        """Test _check_git_available when Git is available."""
        with patch('subprocess.check_output') as mock_check_output:
            mock_check_output.return_value = b"git version 2.34.1"
            assert git_manager._check_git_available() is True

    def test_check_git_available_false(self):
        """Test _check_git_available when Git is not available."""
        with patch('subprocess.check_output', side_effect=OSError("Git not found")):
            assert git_manager._check_git_available() is False

    def test_get_repo_name_from_url_https(self):
        """Test repository name extraction from HTTPS URL."""
        url = "https://github.com/user/repo.git"
        assert git_manager._get_repo_name_from_url(url) == "repo"

    def test_get_repo_name_from_url_ssh(self):
        """Test repository name extraction from SSH URL."""
        url = "git@github.com:user/repo.git"
        assert git_manager._get_repo_name_from_url(url) == "repo"

    def test_get_repo_name_from_url_no_git_extension(self):
        """Test repository name extraction from URL without .git extension."""
        url = "https://github.com/user/repo"
        assert git_manager._get_repo_name_from_url(url) == "repo"

    def test_get_repository_path_with_local_path(self):
        """Test get_repository_path with local path provided."""
        params = {
            'repository_url': 'https://github.com/user/repo.git',
            'local_repository_path': '/custom/path'
        }
        result = git_manager.get_repository_path(params)
        expected = os.path.join('/custom/path', 'repo')
        assert result == expected

    def test_get_repository_path_without_local_path(self):
        """Test get_repository_path without local path provided."""
        params = {
            'repository_url': 'https://github.com/user/repo.git'        }
        result = git_manager.get_repository_path(params)
        assert result is None

    def test_get_repository_path_no_url(self):
        """Test get_repository_path with no URL provided."""
        params = {
            'local_repository_path': '/custom/path'
        }
        result = git_manager.get_repository_path(params)
        assert result is None

    @patch('openscope_experimental_launcher.utils.git_manager._check_git_available')
    def test_setup_repository_git_unavailable(self, mock_git_available):
        """Test setup_repository when Git is not available."""
        mock_git_available.return_value = False
        
        params = {
            'repository_url': 'https://github.com/user/repo.git',
            'repository_commit_hash': 'main',
            'local_repository_path': '/tmp/repos'
        }
        
        result = git_manager.setup_repository(params)
        assert result is False

    @patch('openscope_experimental_launcher.utils.git_manager._check_git_available')
    def test_setup_repository_no_url(self, mock_git_available):
        """Test setup_repository with no URL."""
        mock_git_available.return_value = True
        
        params = {}
        
        result = git_manager.setup_repository(params)
        assert result is True  # Changed: function returns True when no repo config

    @patch('os.path.exists')
    @patch('openscope_experimental_launcher.utils.git_manager._clone_repository')
    @patch('openscope_experimental_launcher.utils.git_manager._check_git_available')
    def test_setup_repository_new_clone_success(self, mock_git_available, mock_clone, mock_exists):
        """Test setup_repository with successful new clone."""
        mock_git_available.return_value = True
        mock_exists.return_value = False
        mock_clone.return_value = True
        
        params = {            'repository_url': 'https://github.com/user/repo.git',
            'repository_commit_hash': 'main',
            'local_repository_path': '/test/path'
        }
        
        result = git_manager.setup_repository(params)
        assert result is True

    @patch('subprocess.check_call')
    def test_clone_repository_success(self, mock_check_call):
        """Test _clone_repository with successful clone."""
        mock_check_call.return_value = None  # check_call returns None on success
        
        result = git_manager._clone_repository(
            'https://github.com/user/repo.git',
            '/path/to/repo'
        )
        assert result is True

    @patch('subprocess.check_call')
    def test_clone_repository_failure(self, mock_check_call):
        """Test _clone_repository with failure."""
        mock_check_call.side_effect = subprocess.CalledProcessError(1, 'git')
        
        result = git_manager._clone_repository(
            'https://github.com/user/repo.git',
            '/path/to/repo'        )
        assert result is False

    @patch('os.chdir')
    @patch('subprocess.check_output')
    def test_get_current_commit_hash_success(self, mock_check_output, mock_chdir):
        """Test _get_current_commit_hash with success."""
        mock_check_output.return_value = b"abc123def456\n"  # Fixed: use real newline
        
        result = git_manager._get_current_commit_hash('/path/to/repo')
        assert result == "abc123def456"

    @patch('os.chdir')
    @patch('subprocess.check_output')
    def test_get_current_commit_hash_failure(self, mock_check_output, mock_chdir):
        """Test _get_current_commit_hash with failure."""
        mock_check_output.side_effect = subprocess.CalledProcessError(1, 'git')
        
        result = git_manager._get_current_commit_hash('/path/to/repo')
        assert result is None

    @patch('shutil.rmtree')
    @patch('os.path.exists')
    def test_force_remove_directory_success(self, mock_exists, mock_rmtree):
        """Test _force_remove_directory with successful removal."""
        mock_exists.return_value = True
        
        result = git_manager._force_remove_directory('/path/to/repo')
        assert result is True
        mock_rmtree.assert_called_once()

    @patch('os.path.exists')
    def test_force_remove_directory_not_exists(self, mock_exists):
        """Test _force_remove_directory with non-existent directory."""
        mock_exists.return_value = False
        
        result = git_manager._force_remove_directory('/path/to/repo')
        assert result is True

    @patch('shutil.rmtree', side_effect=OSError("Permission denied"))
    @patch('os.path.exists')
    def test_force_remove_directory_failure(self, mock_exists, mock_rmtree):
        """Test _force_remove_directory with failure."""
        mock_exists.return_value = True
        
        result = git_manager._force_remove_directory('/path/to/repo')
        assert result is False
