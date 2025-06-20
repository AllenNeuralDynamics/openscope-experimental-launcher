"""
Tests for git manager module.
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock

from src.openscope_experimental_launcher.utils import git_manager


class TestGitManager:
    """Test cases for git manager functions."""

    def test_setup_repository_success(self):
        """Test successful repository setup."""
        params = {
            'repository_url': 'https://github.com/test/repo.git',
            'repository_commit_hash': 'abc123',
            'local_repository_path': '/test/repo'
        }
        
        with patch.object(git_manager, 'clone_repository', return_value=True), \
             patch.object(git_manager, 'checkout_commit', return_value=True):
            result = git_manager.setup_repository(params)
            assert result is True

    def test_setup_repository_no_params(self):
        """Test repository setup with no parameters."""
        params = {}
        result = git_manager.setup_repository(params)
        assert result is True  # Should succeed but do nothing

    def test_setup_repository_clone_failure(self):
        """Test repository setup with clone failure."""
        params = {
            'repository_url': 'https://github.com/test/repo.git',
            'local_repository_path': '/test/repo'
        }
        
        with patch.object(git_manager, 'clone_repository', return_value=False):
            result = git_manager.setup_repository(params)
            assert result is False

    def test_setup_repository_checkout_failure(self):
        """Test repository setup with checkout failure."""
        params = {
            'repository_url': 'https://github.com/test/repo.git',
            'repository_commit_hash': 'abc123',
            'local_repository_path': '/test/repo'
        }
        
        with patch.object(git_manager, 'clone_repository', return_value=True), \
             patch.object(git_manager, 'checkout_commit', return_value=False):
            result = git_manager.setup_repository(params)
            assert result is False

    def test_clone_repository_success(self):
        """Test successful repository cloning."""
        mock_result = Mock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result), \
             patch('os.path.exists', return_value=False):
            result = git_manager.clone_repository(
                'https://github.com/test/repo.git',
                '/test/repo'
            )
            assert result is True

    def test_clone_repository_already_exists(self):
        """Test repository cloning when directory already exists."""
        with patch('os.path.exists', return_value=True):
            result = git_manager.clone_repository(
                'https://github.com/test/repo.git',
                '/test/repo'
            )
            assert result is True

    def test_clone_repository_subprocess_failure(self):
        """Test repository cloning with subprocess failure."""
        mock_result = Mock()
        mock_result.returncode = 1
        
        with patch('subprocess.run', return_value=mock_result), \
             patch('os.path.exists', return_value=False):
            result = git_manager.clone_repository(
                'https://github.com/test/repo.git',
                '/test/repo'
            )
            assert result is False

    def test_clone_repository_exception(self):
        """Test repository cloning with exception."""
        with patch('subprocess.run', side_effect=Exception("Test exception")), \
             patch('os.path.exists', return_value=False):
            result = git_manager.clone_repository(
                'https://github.com/test/repo.git',
                '/test/repo'
            )
            assert result is False

    def test_checkout_commit_success(self):
        """Test successful commit checkout."""
        mock_result = Mock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result), \
             patch('os.path.exists', return_value=True):
            result = git_manager.checkout_commit('/test/repo', 'abc123')
            assert result is True

    def test_checkout_commit_repo_not_exists(self):
        """Test commit checkout when repository doesn't exist."""
        with patch('os.path.exists', return_value=False):
            result = git_manager.checkout_commit('/test/repo', 'abc123')
            assert result is False

    def test_checkout_commit_subprocess_failure(self):
        """Test commit checkout with subprocess failure."""
        mock_result = Mock()
        mock_result.returncode = 1
        
        with patch('subprocess.run', return_value=mock_result), \
             patch('os.path.exists', return_value=True):
            result = git_manager.checkout_commit('/test/repo', 'abc123')
            assert result is False

    def test_checkout_commit_exception(self):
        """Test commit checkout with exception."""
        with patch('subprocess.run', side_effect=Exception("Test exception")), \
             patch('os.path.exists', return_value=True):
            result = git_manager.checkout_commit('/test/repo', 'abc123')
            assert result is False

    def test_get_current_commit_success(self):
        """Test successful current commit retrieval."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = 'abc123def456\n'
        
        with patch('subprocess.run', return_value=mock_result), \
             patch('os.path.exists', return_value=True):
            commit = git_manager.get_current_commit('/test/repo')
            assert commit == 'abc123def456'

    def test_get_current_commit_repo_not_exists(self):
        """Test current commit retrieval when repository doesn't exist."""
        with patch('os.path.exists', return_value=False):
            commit = git_manager.get_current_commit('/test/repo')
            assert commit is None

    def test_get_current_commit_subprocess_failure(self):
        """Test current commit retrieval with subprocess failure."""
        mock_result = Mock()
        mock_result.returncode = 1
        
        with patch('subprocess.run', return_value=mock_result), \
             patch('os.path.exists', return_value=True):
            commit = git_manager.get_current_commit('/test/repo')
            assert commit is None

    def test_get_current_commit_exception(self):
        """Test current commit retrieval with exception."""
        with patch('subprocess.run', side_effect=Exception("Test exception")), \
             patch('os.path.exists', return_value=True):
            commit = git_manager.get_current_commit('/test/repo')
            assert commit is None

    def test_get_repository_status_success(self):
        """Test successful repository status retrieval."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = 'M  modified_file.py\n?? untracked_file.py\n'
        
        with patch('subprocess.run', return_value=mock_result), \
             patch('os.path.exists', return_value=True):
            status = git_manager.get_repository_status('/test/repo')
            assert 'M  modified_file.py' in status
            assert '?? untracked_file.py' in status

    def test_get_repository_status_repo_not_exists(self):
        """Test repository status retrieval when repository doesn't exist."""
        with patch('os.path.exists', return_value=False):
            status = git_manager.get_repository_status('/test/repo')
            assert status is None

    def test_get_repository_status_subprocess_failure(self):
        """Test repository status retrieval with subprocess failure."""
        mock_result = Mock()
        mock_result.returncode = 1
        
        with patch('subprocess.run', return_value=mock_result), \
             patch('os.path.exists', return_value=True):
            status = git_manager.get_repository_status('/test/repo')
            assert status is None

    def test_get_repository_status_exception(self):
        """Test repository status retrieval with exception."""
        with patch('subprocess.run', side_effect=Exception("Test exception")), \
             patch('os.path.exists', return_value=True):
            status = git_manager.get_repository_status('/test/repo')
            assert status is None

    def test_validate_repository_success(self):
        """Test successful repository validation."""
        with patch('os.path.exists', return_value=True), \
             patch('os.path.isdir', return_value=True):
            result = git_manager.validate_repository('/test/repo')
            assert result is True

    def test_validate_repository_not_exists(self):
        """Test repository validation when directory doesn't exist."""
        with patch('os.path.exists', return_value=False):
            result = git_manager.validate_repository('/test/repo')
            assert result is False

    def test_validate_repository_not_git_repo(self):
        """Test repository validation when directory exists but no .git folder."""
        with patch('os.path.exists', side_effect=lambda path: not path.endswith('.git')):
            result = git_manager.validate_repository('/test/repo')
            assert result is False

    def test_pull_latest_changes_success(self):
        """Test successful pulling of latest changes."""
        mock_result = Mock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result), \
             patch('os.path.exists', return_value=True):
            result = git_manager.pull_latest_changes('/test/repo')
            assert result is True

    def test_pull_latest_changes_repo_not_exists(self):
        """Test pulling latest changes when repository doesn't exist."""
        with patch('os.path.exists', return_value=False):
            result = git_manager.pull_latest_changes('/test/repo')
            assert result is False

    def test_pull_latest_changes_subprocess_failure(self):
        """Test pulling latest changes with subprocess failure."""
        mock_result = Mock()
        mock_result.returncode = 1
        
        with patch('subprocess.run', return_value=mock_result), \
             patch('os.path.exists', return_value=True):
            result = git_manager.pull_latest_changes('/test/repo')
            assert result is False

    def test_pull_latest_changes_exception(self):
        """Test pulling latest changes with exception."""
        with patch('subprocess.run', side_effect=Exception("Test exception")), \
             patch('os.path.exists', return_value=True):
            result = git_manager.pull_latest_changes('/test/repo')
            assert result is False

    def test_create_branch_success(self):
        """Test successful branch creation."""
        mock_result = Mock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result), \
             patch('os.path.exists', return_value=True):
            result = git_manager.create_branch('/test/repo', 'new_branch')
            assert result is True

    def test_create_branch_repo_not_exists(self):
        """Test branch creation when repository doesn't exist."""
        with patch('os.path.exists', return_value=False):
            result = git_manager.create_branch('/test/repo', 'new_branch')
            assert result is False

    def test_create_branch_subprocess_failure(self):
        """Test branch creation with subprocess failure."""
        mock_result = Mock()
        mock_result.returncode = 1
        
        with patch('subprocess.run', return_value=mock_result), \
             patch('os.path.exists', return_value=True):
            result = git_manager.create_branch('/test/repo', 'new_branch')
            assert result is False

    def test_create_branch_exception(self):
        """Test branch creation with exception."""
        with patch('subprocess.run', side_effect=Exception("Test exception")), \
             patch('os.path.exists', return_value=True):
            result = git_manager.create_branch('/test/repo', 'new_branch')
            assert result is False

    def test_switch_branch_success(self):
        """Test successful branch switching."""
        mock_result = Mock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result), \
             patch('os.path.exists', return_value=True):
            result = git_manager.switch_branch('/test/repo', 'target_branch')
            assert result is True

    def test_switch_branch_repo_not_exists(self):
        """Test branch switching when repository doesn't exist."""
        with patch('os.path.exists', return_value=False):
            result = git_manager.switch_branch('/test/repo', 'target_branch')
            assert result is False

    def test_switch_branch_subprocess_failure(self):
        """Test branch switching with subprocess failure."""
        mock_result = Mock()
        mock_result.returncode = 1
        
        with patch('subprocess.run', return_value=mock_result), \
             patch('os.path.exists', return_value=True):
            result = git_manager.switch_branch('/test/repo', 'target_branch')
            assert result is False

    def test_switch_branch_exception(self):
        """Test branch switching with exception."""
        with patch('subprocess.run', side_effect=Exception("Test exception")), \
             patch('os.path.exists', return_value=True):
            result = git_manager.switch_branch('/test/repo', 'target_branch')
            assert result is False
