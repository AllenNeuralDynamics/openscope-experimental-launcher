"""
Bonsai launcher for OpenScope experiments.

This module provides a launcher for running Bonsai workflows with
Windows-specific optimizations.
"""

import os
import logging
import subprocess
import datetime
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
    
    def get_data_streams(self, start_time: datetime.datetime, end_time: datetime.datetime) -> list:
        """
        Get data streams for Bonsai experiments.
        
        Extends base launcher stream with Bonsai-specific stream.
        
        Args:
            start_time: Session start time
            end_time: Session end time
            
        Returns:
            List containing launcher stream + Bonsai stream
        """
        import datetime
        from aind_data_schema.core.session import Stream
        from aind_data_schema.components.devices import Software
        from aind_data_schema_models.modalities import Modality
        
        # Get base launcher stream
        streams = super().get_data_streams(start_time, end_time)
          # Add Bonsai script stream
        try:
            script_path = self.params.get('script_path', 'Unknown')
            script_name = os.path.basename(script_path) if script_path != 'Unknown' else 'Unknown'
            script_parameters = self.params.get("script_parameters", {})

            bonsai_script_stream = Stream(
                stream_start_time=start_time,
                stream_end_time=end_time,
                stream_modalities=[Modality.BEHAVIOR],
                software=[Software(
                    name=f"Bonsai Script: {script_name}",
                    version=self.params.get("script_version", "Unknown"),
                    url=script_path,
                    parameters=script_parameters
                )]
            )
            streams.append(bonsai_script_stream)
        except Exception as e:
            logging.warning(f"Could not create Bonsai script stream: {e}")
        
        return streams
