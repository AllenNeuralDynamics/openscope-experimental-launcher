"""
Bonsai launcher for OpenScope experiments.

This module provides a launcher for running Bonsai workflows with
Windows-specific optimizations.
"""

import os
import logging
import subprocess
from typing import Dict, Optional

# Import Windows-specific modules for process management
try:
    import win32job
    import win32api
    import win32con
    WINDOWS_MODULES_AVAILABLE = True
except ImportError:
    WINDOWS_MODULES_AVAILABLE = False
    logging.warning("Windows modules not available. Process management will be limited.")

from .base_launcher import BaseLauncher
from ..interfaces import bonsai_interface
from ..utils import git_manager


class BonsaiLauncher(BaseLauncher):
    """
    Launcher for Bonsai-based OpenScope experiments.
    
    Extends BaseLauncher with Bonsai-specific process creation and
    Windows job object handling for enhanced process management.    """
    
    def __init__(self, param_file: Optional[str] = None, rig_config_path: Optional[str] = None):
        """Initialize the Bonsai launcher.
        
        Args:
            param_file: Path to JSON file containing experiment-specific parameters.
            rig_config_path: Optional override path to rig config file.
        """
        super().__init__(param_file, rig_config_path)
        
        # Windows job object for process management
        self.hJob = None
        if WINDOWS_MODULES_AVAILABLE:
            self._setup_windows_job()
    
    def _setup_windows_job(self):
        """Set up Windows job object for process management."""
        try:
            self.hJob = win32job.CreateJobObject(None, "BonsaiJobObject")
            extended_info = win32job.QueryInformationJobObject(
                self.hJob, win32job.JobObjectExtendedLimitInformation
            )
            extended_info['BasicLimitInformation']['LimitFlags'] = (
                win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            )
            win32job.SetInformationJobObject(
                self.hJob, win32job.JobObjectExtendedLimitInformation, extended_info
            )
            logging.info("Windows job object created for process management")
        except Exception as e:
            logging.warning(f"Failed to create Windows job object: {e}")
            self.hJob = None
    
    def _get_launcher_type_name(self) -> str:
        """Get the name of the launcher type for logging."""
        return "Bonsai"
    
    def _resolve_bonsai_paths(self) -> Dict[str, str]:
        """
        Resolve all Bonsai-related paths relative to the repository.
        
        Returns:
            Dictionary with resolved absolute paths for Bonsai components
        """
        repo_path = git_manager.get_repository_path(self.params)
        resolved_params = {}
        
        # List of path parameters that should be resolved relative to repo
        path_params = [
            'bonsai_exe_path',
            'bonsai_setup_script', 
            'bonsai_config_path'
        ]
        
        for param_name in path_params:
            param_value = self.params.get(param_name)
            if param_value:
                if os.path.isabs(param_value):
                    # Already absolute path
                    resolved_params[param_name] = param_value
                elif repo_path:
                    # Resolve relative to repository
                    resolved_params[param_name] = os.path.join(repo_path, param_value)
                else:
                    # No repository path available, use as-is
                    resolved_params[param_name] = param_value                    
        return resolved_params

    def _assign_to_job_object(self):
        """Assign Bonsai process to Windows job object."""
        if not (WINDOWS_MODULES_AVAILABLE and self.hJob and self.process):
            return
            
        try:
            perms = win32con.PROCESS_TERMINATE | win32con.PROCESS_SET_QUOTA
            hProcess = win32api.OpenProcess(perms, False, self.process.pid)
            win32job.AssignProcessToJobObject(self.hJob, hProcess)
            logging.info(f"Bonsai process {self.process.pid} assigned to job object")
        except Exception as e:
            logging.warning(f"Failed to assign process to job object: {e}")
    
    def create_process(self) -> subprocess.Popen:
        """
        Create the Bonsai subprocess.
        
        Returns:
            subprocess.Popen object for the running Bonsai workflow
        """
        # Resolve all Bonsai paths relative to repository
        resolved_paths = self._resolve_bonsai_paths()
        
        # Create updated params with resolved paths
        bonsai_params = self.params.copy()
        bonsai_params.update(resolved_paths)
        
        # Setup Bonsai environment (including installation if needed)
        if not bonsai_interface.setup_bonsai_environment(bonsai_params):
            raise RuntimeError("Failed to setup Bonsai environment")
          # Get workflow path
        workflow_path = self._get_script_path()
        
        # Construct arguments using BonsaiInterface
        workflow_args = bonsai_interface.construct_workflow_arguments(self.params)
        
        # Start workflow using BonsaiInterface
        process = bonsai_interface.start_workflow(
            workflow_path=workflow_path,
            bonsai_exe_path=bonsai_params.get('bonsai_exe_path'),
            arguments=workflow_args,
            output_folder=self.output_session_folder
        )
        
        # Assign process to Windows job object if available
        if process and WINDOWS_MODULES_AVAILABLE and self.hJob:
            # Store process temporarily to use in _assign_to_job_object
            self.process = process
            self._assign_to_job_object()
        
        return process

    @staticmethod
    def run_post_processing(session_directory: str) -> bool:
        """
        Bonsai-specific post-processing using unified param_file workflow.
        Calls session_creator and session_enhancer_bonsai run_postprocessing APIs.
        Returns True if both steps succeed, False otherwise.
        """
        logging.info(f"Running Bonsai post-processing for: {session_directory}")
        metadata_dir = os.path.join(session_directory, "launcher_metadata")
        param_file = os.path.join(metadata_dir, "processed_parameters.json")
        from openscope_experimental_launcher.post_processing import session_creator
        from openscope_experimental_launcher.post_processing import session_enhancer_bonsai
        result1 = session_creator.run_postprocessing(param_file=param_file)
        if result1 != 0:
            logging.error(f"Session creation post-processing failed (exit code {result1})")
            return False
        result2 = session_enhancer_bonsai.run_postprocessing(param_file=param_file)
        if result2 != 0:
            logging.warning(f"Bonsai session enhancement failed (exit code {result2}), but base session exists")
        else:
            logging.info("Bonsai session enhancement completed successfully")
        logging.info("Bonsai post-processing completed successfully")
        return True
