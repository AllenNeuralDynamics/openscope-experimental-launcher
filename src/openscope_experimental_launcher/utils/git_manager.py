"""
Git repository management for OpenScope experimental launchers.

Handles cloning, updating, and version management of workflow repositories.
"""

import os
import logging
import subprocess
import shutil
import stat
from pathlib import Path
from typing import Dict, Any, Optional, Union


def _check_git_available() -> bool:
    """Check if Git is available on the system."""
    try:
        subprocess.check_output(['git', '--version'], stderr=subprocess.STDOUT)
        return True
    except (subprocess.CalledProcessError, OSError):
        logging.error("Git is not available on this system. Please install Git to use repository management features.")
        return False


def _get_repo_name_from_url(repo_url: str) -> str:
    """Extract repository name from Git URL."""
    # Remove trailing slash if present
    repo_url = repo_url.rstrip('/')
    
    # Handle both HTTPS and SSH URLs
    if repo_url.endswith('.git'):
        repo_name = os.path.basename(repo_url)[:-4]
    else:
        repo_name = os.path.basename(repo_url)
    return repo_name


def _get_current_commit_hash(repo_path: str) -> Optional[str]:
    """Get the current commit hash of a Git repository."""
    try:
        original_dir = os.getcwd()
        os.chdir(repo_path)
        commit_hash = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], 
            stderr=subprocess.STDOUT
        ).decode().strip()
        return commit_hash
    except (subprocess.CalledProcessError, OSError) as e:
        logging.warning(f"Failed to get current commit hash: {e}")
        return None
    finally:
        os.chdir(original_dir)


def _get_remote_commit_hash(repo_path: str, branch: str = 'main') -> Optional[str]:
    """Get the latest commit hash from the remote repository for a specific branch."""
    try:
        original_dir = os.getcwd()
        os.chdir(repo_path)
        
        # Fetch latest changes from remote
        subprocess.check_call(['git', 'fetch', 'origin'], stderr=subprocess.STDOUT)
        
        # Get the commit hash of the remote branch
        remote_commit = subprocess.check_output(
            ['git', 'rev-parse', f'origin/{branch}'], 
            stderr=subprocess.STDOUT
        ).decode().strip()
        return remote_commit
    except (subprocess.CalledProcessError, OSError) as e:
        logging.warning(f"Failed to get remote commit hash for {branch}: {e}")
        return None
    finally:
        os.chdir(original_dir)


def _is_on_target_commit(repo_path: str, target_commit: str) -> bool:
    """Check if the repository is on the target commit."""
    if target_commit == 'main':
        # For main branch, check against remote origin/main
        current_hash = _get_current_commit_hash(repo_path)
        remote_hash = _get_remote_commit_hash(repo_path, 'main')
        
        if current_hash and remote_hash:
            if current_hash == remote_hash:
                logging.info("Repository is on the latest commit of main branch")
                return True
            else:
                logging.info("Repository is not on the latest commit")
                logging.info(f"Current: {current_hash[:8]}, Latest remote: {remote_hash[:8]}")
                return False
        else:
            logging.warning("Could not compare commit hashes")
            return False
    else:
        # For specific commit hash, check if current commit matches
        current_hash = _get_current_commit_hash(repo_path)
        if current_hash and current_hash.startswith(target_commit):
            logging.info(f"Repository is at the specified commit: {target_commit}")
            return True
        else:
            logging.info("Repository is not at the specified commit")
            logging.info(f"Current: {current_hash[:8] if current_hash else 'unknown'}, Required: {target_commit}")
            return False


def _clone_repository(repo_url: str, local_path: str) -> bool:
    """Clone a Git repository to the specified local path."""
    try:
        logging.info(f"Cloning repository {repo_url} to {local_path}")
        
        # Create parent directory if it doesn't exist
        parent_dir = os.path.dirname(local_path)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        
        # Clone the repository
        subprocess.check_call(
            ['git', 'clone', repo_url, local_path], 
            stderr=subprocess.STDOUT
        )
        logging.info("Repository cloned successfully")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to clone repository: {e}")
        return False
    except OSError as e:
        logging.error(f"Git command failed: {e}")
        return False


def _checkout_commit(repo_path: str, commit_hash: str) -> bool:
    """Checkout a specific commit in the repository."""
    try:
        original_dir = os.getcwd()
        os.chdir(repo_path)
        
        logging.info(f"Checking out commit {commit_hash}")
        
        # Fetch latest changes first
        subprocess.check_call(['git', 'fetch'], stderr=subprocess.STDOUT)
        
        # Checkout the specific commit
        subprocess.check_call(['git', 'checkout', commit_hash], stderr=subprocess.STDOUT)
        
        logging.info(f"Successfully checked out commit {commit_hash}")
        return True
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to checkout commit {commit_hash}: {e}")
        return False
    except OSError as e:
        logging.error(f"Git command failed: {e}")
        return False
    finally:
        os.chdir(original_dir)


def _update_repository(repo_path: str, commit_hash: str) -> bool:
    """Update an existing repository to the specified commit using Git operations."""
    try:
        original_dir = os.getcwd()
        os.chdir(repo_path)
        
        logging.info(f"Updating existing repository to commit {commit_hash}")
        
        # Reset any local changes
        subprocess.check_call(['git', 'reset', '--hard'], stderr=subprocess.STDOUT)
        
        # Fetch latest changes
        subprocess.check_call(['git', 'fetch', 'origin'], stderr=subprocess.STDOUT)
        
        # Checkout the target commit/branch
        if commit_hash == 'main':
            subprocess.check_call(['git', 'checkout', 'main'], stderr=subprocess.STDOUT)
            subprocess.check_call(['git', 'pull', 'origin', 'main'], stderr=subprocess.STDOUT)
        else:
            subprocess.check_call(['git', 'checkout', commit_hash], stderr=subprocess.STDOUT)
        
        return True
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to update repository: {e}")
        return False
    except OSError as e:
        logging.error(f"Git command failed: {e}")
        return False
    finally:
        os.chdir(original_dir)


def _force_remove_directory(path: str) -> bool:
    """Force remove a directory, handling Windows file locks."""
    def handle_remove_readonly(func, path, exc):
        """Error handler for Windows readonly files."""
        if os.path.exists(path):
            os.chmod(path, stat.S_IWRITE)
            func(path)
    
    try:
        logging.info(f"Removing directory: {path}")
        shutil.rmtree(path, onerror=handle_remove_readonly)
        return True
    except Exception as e:
        logging.error(f"Failed to remove directory {path}: {e}")
        return False


def setup_repository(params: Dict[str, Any]) -> bool:
    """
    Set up the repository based on parameters.
    
    Args:
        params: Dictionary containing repository configuration
        
    Returns:
        True if successful, False otherwise
    """
    repo_url = params.get('repository_url')
    commit_hash = params.get('repository_commit_hash', 'main')
    local_repo_path = params.get('local_repository_path')
    
    if not repo_url or not local_repo_path:
        logging.info("No repository configuration found, skipping repository setup")
        return True
    
    if not _check_git_available():
        return False
    
    logging.info(f"Setting up repository: {repo_url}")
    logging.info(f"Target commit: {commit_hash}")
    logging.info(f"Local path: {local_repo_path}")
    
    # Determine repository name from URL
    repo_name = _get_repo_name_from_url(repo_url)
    repo_full_path = os.path.join(local_repo_path, repo_name)
    
    # Check if repository already exists
    if os.path.exists(repo_full_path):
        if os.path.exists(os.path.join(repo_full_path, '.git')):
            logging.info("Repository already exists, checking commit hash")
            
            if _is_on_target_commit(repo_full_path, commit_hash):
                logging.info("Repository is already at the correct commit")
                return True
            else:
                logging.info("Repository needs to be updated")
                if _update_repository(repo_full_path, commit_hash):
                    logging.info("Repository updated successfully")
                    return True
                else:
                    logging.warning("Failed to update repository, will try fresh clone")
                    if not _force_remove_directory(repo_full_path):
                        logging.error("Failed to remove existing repository for fresh clone")
                        return False
        else:
            logging.info("Directory exists but is not a Git repository, removing it")
            if not _force_remove_directory(repo_full_path):
                logging.error("Failed to remove existing directory")
                return False
    
    # Clone the repository
    if not _clone_repository(repo_url, repo_full_path):
        return False
    
    # Checkout specific commit if not 'main'
    if commit_hash != 'main':
        if not _checkout_commit(repo_full_path, commit_hash):
            return False
    
    logging.info("Repository setup completed successfully")
    return True


def get_repository_path(params: Dict[str, Any]) -> Optional[str]:
    """
    Get the full path to the cloned repository.
    
    Args:
        params: Dictionary containing repository configuration
        
    Returns:
        Path to repository or None if not configured
    """
    local_repo_path = params.get('local_repository_path')
    repo_url = params.get('repository_url')
    
    if not local_repo_path or not repo_url:
        return None
    
    repo_name = _get_repo_name_from_url(repo_url)
    return os.path.join(local_repo_path, repo_name)


def find_repo_root(start_path: Union[str, Path]) -> Optional[str]:
    """Walk upward from start_path to find the nearest git repo root."""
    path = Path(start_path).resolve()
    for candidate in [path, *path.parents]:
        if (candidate / ".git").exists():
            return str(candidate)
    return None


def get_current_commit(repo_path: Union[str, Path]) -> Optional[str]:
    """Public helper to return HEAD commit hash for a repo path."""
    repo_path = Path(repo_path)
    if not repo_path.exists() or not (repo_path / ".git").exists():
        return None
    if not _check_git_available():
        return None
    return _get_current_commit_hash(str(repo_path))
