"""
Bonsai launcher for OpenScope experiments.

This module provides a launcher for running Bonsai workflows with
Windows-specific optimizations.
"""

import os
import logging
import subprocess
import time
import re
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
    # No additional Bonsai-specific error handling; BaseLauncher generic monitoring used.
    
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

    def _get_script_path(self) -> str:
        """Resolve and return absolute path to Bonsai workflow (.bonsai file).

        Uses 'script_path' from params, resolves relative to repository path if not absolute.
        Raises RuntimeError if path is missing or file does not exist.
        """
        script_path = self.params.get('script_path')
        if not script_path:
            raise RuntimeError("Missing 'script_path' parameter for Bonsai workflow")
        if os.path.isabs(script_path):
            candidate = script_path
        else:
            repo_root = git_manager.get_repository_path(self.params)
            candidate = os.path.join(repo_root, script_path) if repo_root else script_path
        if not os.path.isfile(candidate):
            raise RuntimeError(f"Bonsai workflow not found: {candidate}")
        logging.info(f"Using Bonsai workflow: {candidate}")
        return candidate

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

    def start_experiment(self) -> bool:
        """Start Bonsai with optional retry-on-failure logic.

        Default behavior: on failure, ask the operator whether to retry (default yes).

        Controlled via params:
        - bonsai_max_retries (int | null): maximum retries after the first attempt.
          If omitted/null -> unlimited retries (until operator says no).
          If 0 -> no retries (fail immediately).
        - bonsai_retry_delay_sec (float): delay between retries (default 0)
        - bonsai_fail_on_stderr (bool): treat any stderr output as failure (default False)
        - bonsai_retry_error_patterns (list[str]): regex patterns; if any match stdout/stderr, treat as failure
        """

        max_retries_raw = self.params.get("bonsai_max_retries", None)
        max_retries: Optional[int]
        if max_retries_raw is None or str(max_retries_raw).strip() == "":
            max_retries = None
        else:
            max_retries = int(max_retries_raw)
            if max_retries < 0:
                max_retries = None

        retry_delay = float(self.params.get("bonsai_retry_delay_sec", 0) or 0)
        fail_on_stderr = bool(self.params.get("bonsai_fail_on_stderr", False))
        patterns = self.params.get("bonsai_retry_error_patterns") or []
        if isinstance(patterns, str):
            patterns = [patterns]
        compiled_patterns = []
        for pat in patterns:
            try:
                compiled_patterns.append(re.compile(str(pat)))
            except re.error:
                logging.warning("Invalid regex in bonsai_retry_error_patterns: %r", pat)

        attempt = 1
        retries_used = 0
        while True:
            # Reset per-attempt buffers so we don't show stale errors.
            self.stdout_data = []
            self.stderr_data = []
            if hasattr(self, "_first_stderr_ts"):
                try:
                    delattr(self, "_first_stderr_ts")
                except Exception:
                    pass

            logging.info(
                "Starting Bonsai workflow attempt %d (retries used: %d)",
                attempt,
                retries_used,
            )

            self.process = self.create_process()
            if self.process is None:
                logging.error("Failed to create Bonsai process")
                return False

            self._start_output_readers()
            logging.info("Bonsai PID: %s", getattr(self.process, "pid", "unknown"))

            self._monitor_process()
            try:
                self.process.wait(timeout=0.1)
            except Exception:
                pass

            rc = getattr(self.process, "returncode", None)

            failure_reason = None
            if rc not in (None, 0):
                failure_reason = f"exit code {rc}"
            elif fail_on_stderr and getattr(self, "stderr_data", None):
                failure_reason = "stderr output detected"
            elif compiled_patterns:
                combined = (getattr(self, "stdout_data", []) or []) + (getattr(self, "stderr_data", []) or [])
                for line in combined:
                    for cre in compiled_patterns:
                        if cre.search(str(line)):
                            failure_reason = f"log matched pattern {cre.pattern!r}"
                            break
                    if failure_reason:
                        break

            if failure_reason is None:
                return True

            remaining = None if max_retries is None else max(0, max_retries - retries_used)
            logging.error(
                "Bonsai workflow failed (%s). Remaining retries: %s",
                failure_reason,
                "unlimited" if remaining is None else str(remaining),
            )

            # Surface some context for the operator.
            tail = (getattr(self, "stderr_data", []) or [])[-10:]
            for line in tail:
                if str(line).strip():
                    logging.error("Bonsai stderr: %s", line)

            # Enforce optional cap.
            if max_retries == 0:
                return False
            if max_retries is not None and retries_used >= max_retries:
                return False

            # Default behavior: prompt operator to retry (default yes).
            try:
                from openscope_experimental_launcher.utils import param_utils

                ans = param_utils.get_user_input(
                    f"Bonsai workflow failed ({failure_reason}). Retry? [y/n]",
                    default="y",
                    cast_func=str,
                )
                do_retry = str(ans).strip().lower() in {"y", "yes", "1", "true"}
            except Exception:
                # If we cannot prompt, fail closed (do not loop unexpectedly).
                do_retry = False

            if not do_retry:
                return False

            if retry_delay > 0:
                time.sleep(retry_delay)

            retries_used += 1
            attempt += 1

    # No _start_output_readers override; inherit BaseLauncher behavior for stdout/stderr logging.

def run_from_params(param_file, *, log_level=None):
    """
    Module-level entry point for the unified launcher wrapper.
    Calls BonsaiLauncher.run_from_params.
    """
    return BonsaiLauncher.run_from_params(param_file, log_level=log_level)