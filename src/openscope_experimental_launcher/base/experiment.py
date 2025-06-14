"""
Base experiment launcher class for OpenScope Bonsai workflows.

This module contains the core functionality for launching Bonsai workflows
with parameter management, process monitoring, and basic metadata collection.
"""

import os
import sys
import time
import signal
import logging
import datetime
import platform
import subprocess
import socket
import uuid
import hashlib
import atexit
import psutil
import threading
import shutil
import json
import yaml
from typing import Dict, List, Optional, Any
from decimal import Decimal

# Import Windows-specific modules for process management
try:
    import win32job
    import win32api
    import win32con
    WINDOWS_MODULES_AVAILABLE = True
except ImportError:
    WINDOWS_MODULES_AVAILABLE = False
    logging.warning("Windows modules not available. Process management will be limited.")

from ..utils.config_loader import ConfigLoader
from ..utils.git_manager import GitManager
from ..utils.process_monitor import ProcessMonitor


class BaseExperiment:
    """
    Base class for OpenScope experimental launchers.
    
    Provides core functionality for:
    - Parameter loading and management
    - Bonsai process management
    - Repository setup and version control
    - Process monitoring and memory management
    - Basic output file generation
    """
    
    def __init__(self):
        """Initialize the base experiment with core functionality."""
        self.platform_info = self._get_platform_info()
        self.output_path = None
        self.params = {}
        self.bonsai_process = None
        self.start_time = None
        self.stop_time = None
        self.config = {}
        
        # Session tracking variables
        self.mouse_id = ""
        self.user_id = ""
        self.session_uuid = str(uuid.uuid4())
        self.session_output_path = ""
        self.script_checksum = None
        self.params_checksum = None
        
        # Process monitoring
        self._percent_used = None
        self._restarted = False
        self.stdout_data = []
        self.stderr_data = []
        self._output_threads = []
        
        # Initialize utility classes
        self.config_loader = ConfigLoader()
        self.git_manager = GitManager()
        self.process_monitor = ProcessMonitor()
        
        # Windows job object for process management
        self.hJob = None
        if WINDOWS_MODULES_AVAILABLE:
            self._setup_windows_job()
        
        # Register exit handlers
        atexit.register(self.cleanup)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        logging.info("BaseExperiment initialized")
    
    def _get_platform_info(self) -> Dict[str, Any]:
        """Get system and version information for Windows."""
        return {
            "python": sys.version.split()[0],
            "os": ("Windows", platform.release(), platform.version()),
            "hardware": (platform.processor(), platform.machine()),
            "computer_name": platform.node(),
            "rig_id": os.environ.get('RIG_ID', socket.gethostname()),
        }
    
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
    
    def collect_runtime_information(self) -> Dict[str, str]:
        """
        Collect key information from user at runtime.
        
        This method can be extended in derived classes to collect 
        rig-specific information.
        
        Returns:
            Dictionary containing collected runtime information
        """
        runtime_info = {}
        
        # Only collect subject_id if not already provided in params
        if not self.params.get("mouse_id") and not self.params.get("subject_id"):
            try:
                subject_id = input("Enter subject ID (default: test_subject): ").strip()
                if not subject_id:
                    subject_id = "test_subject"
            except (EOFError, OSError):
                # Handle cases where input is not available (e.g., during testing)
                subject_id = "test_subject"
            runtime_info["subject_id"] = subject_id
        
        # Only collect experimenter_name if not already provided in params
        if not self.params.get("user_id") and not self.params.get("experimenter_name"):
            try:
                experimenter_name = input("Enter experimenter name (default: test_experimenter): ").strip()
                if not experimenter_name:
                    experimenter_name = "test_experimenter"
            except (EOFError, OSError):
                # Handle cases where input is not available (e.g., during testing)
                experimenter_name = "test_experimenter"
            runtime_info["experimenter_name"] = experimenter_name
        
        logging.info(f"Collected runtime info - {runtime_info}")
        return runtime_info

    def load_parameters(self, param_file: Optional[str]):
        """
        Load parameters from a JSON file.
        
        Args:
            param_file: Path to the JSON parameter file
        """
        if param_file:
            with open(param_file, 'r') as f:
                self.params = json.load(f)
                logging.info(f"Loaded parameters from {param_file}")
                
            # Generate parameter checksum for provenance tracking
            with open(param_file, 'rb') as f:
                self.params_checksum = hashlib.md5(f.read()).hexdigest()
            logging.info(f"Parameter file checksum: {self.params_checksum}")
        else:
            logging.warning("No parameter file provided, using default parameters")
            self.params = {}
        
        # Collect runtime information (only for missing values)
        runtime_info = self.collect_runtime_information()
        
        # Update parameters with runtime information
        self.params.update(runtime_info)
        
        # Extract mouse_id and user_id (using runtime info as fallback)
        self.mouse_id = self.params.get("subject_id") or self.params.get("mouse_id", "")
        self.user_id = self.params.get("experimenter_name") or self.params.get("user_id", "")
        
        # Load hardware configuration
        self.config = self.config_loader.load_config(self.params)
        
        # Update mouse_id and user_id from config if still not set
        if not self.mouse_id:
            self.mouse_id = self.config.get("Behavior", {}).get("mouse_id", "test_mouse")
            self.params["mouse_id"] = self.mouse_id
            
        if not self.user_id:
            self.user_id = self.config.get("Behavior", {}).get("user_id", "test_user")
            self.params["user_id"] = self.user_id
        
        logging.info(f"Using mouse_id: {self.mouse_id}, user_id: {self.user_id}")
    
    def setup_output_path(self, output_path: Optional[str] = None) -> str:
        """
        Set up the output path for experiment data.
        
        Args:
            output_path: Specific output path to use
            
        Returns:
            The output file path
        """
        if output_path:
            output_folder = os.path.dirname(output_path)
            if not os.path.isdir(output_folder):
                os.makedirs(output_folder)
            self.session_output_path = output_path
        else:
            # Generate output path based on datetime, mouse ID, and session UUID
            dt_str = datetime.datetime.now().strftime('%y%m%d%H%M%S')
            mouse_id = self.mouse_id if self.mouse_id else "unknown_mouse"
            filename = f"{dt_str}_{mouse_id}_{self.session_uuid}.pkl"
            
            # Default output directory
            output_dir = self.params.get("output_directory", "data")
            if not os.path.isdir(output_dir):
                os.makedirs(output_dir)
                
            self.session_output_path = os.path.join(output_dir, filename)
        
        logging.info(f"Session output path: {self.session_output_path}")
        self.params["output_path"] = self.session_output_path
        
        return self.session_output_path
    
    def create_bonsai_arguments(self) -> List[str]:
        """
        Create command-line arguments for Bonsai.
        
        Only passes properties that are explicitly requested in bonsai_parameters
        to avoid conflicts with workflows that don't have these properties defined.
        
        Returns:
            List of --property arguments for Bonsai
        """
        bonsai_args = []
        
        # Only add parameters from bonsai_parameters section - no automatic defaults
        bonsai_parameters = self.params.get("bonsai_parameters", {})
        if bonsai_parameters:
            logging.info(f"Adding {len(bonsai_parameters)} custom Bonsai parameters")
            for param_name, param_value in bonsai_parameters.items():
                # Convert parameter value to string for Bonsai
                param_str = str(param_value)
                bonsai_args.extend(["--property", f"{param_name}={param_str}"])
                logging.info(f"Added Bonsai parameter: {param_name}={param_str}")
        else:
            logging.info("No custom Bonsai parameters specified - running workflow with defaults")
        
        logging.info(f"Created {len(bonsai_args) // 2} Bonsai arguments")
        return bonsai_args
    
    def start_bonsai(self):
        """Start the Bonsai workflow as a subprocess."""
        logging.info(f"Mouse ID: {self.mouse_id}, User ID: {self.user_id}, Session UUID: {self.session_uuid}")
        
        # Store current memory usage
        vmem = psutil.virtual_memory()
        self._percent_used = vmem.percent
        
        # Ensure output path is set up
        self.setup_output_path(self.params.get("output_path", None))
        
        # Get command-line arguments
        args = self._get_bonsai_args()
        
        logging.info(f"Starting Bonsai with arguments: {' '.join(args)}")
        
        try:
            # Start Bonsai as subprocess
            self.bonsai_process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            # Create threads to read output streams
            self._start_output_readers()
            
            # Assign process to Windows job object if available
            if WINDOWS_MODULES_AVAILABLE and self.hJob:
                self._assign_to_job_object()
            
            self.start_time = datetime.datetime.now()
            logging.info(f"Bonsai started at {self.start_time}")
            
            # Log experiment start
            logging.info(f"MID, {self.mouse_id}, UID, {self.user_id}, Action, Executing, "
                        f"Checksum, {self.script_checksum}, Json_checksum, {self.params_checksum}")
            
            # Monitor Bonsai process
            self._monitor_bonsai()
            
        except Exception as e:
            logging.error(f"Failed to start Bonsai: {e}")
            raise
    
    def _get_bonsai_args(self) -> List[str]:
        """Construct command-line arguments for Bonsai."""
        bonsai_path = self.params.get('bonsai_path')
        if not bonsai_path:
            raise ValueError("No Bonsai workflow path specified in parameters")
        
        # Get Bonsai executable path
        bonsai_exe = self.params.get('bonsai_exe_path', 'Bonsai.exe')
        if not os.path.isabs(bonsai_exe):
            # Try to find Bonsai executable in repository
            repo_path = self.git_manager.get_repository_path(self.params)
            if repo_path:
                bonsai_exe = os.path.join(repo_path, bonsai_exe)
        
        # Get workflow path
        workflow_path = bonsai_path
        if not os.path.isabs(workflow_path):
            repo_path = self.git_manager.get_repository_path(self.params)
            if repo_path:
                workflow_path = os.path.join(repo_path, workflow_path)
        
        if not os.path.exists(workflow_path):
            raise ValueError(f"Bonsai workflow not found at: {workflow_path}")
        
        # Generate workflow checksum
        with open(workflow_path, 'rb') as f:
            self.script_checksum = hashlib.md5(f.read()).hexdigest()
        logging.info(f"Workflow file checksum: {self.script_checksum}")
        
        # Build command arguments
        args = [bonsai_exe, workflow_path, "--start", "--no-editor"]
        
        # Add property arguments
        bonsai_property_args = self.create_bonsai_arguments()
        args.extend(bonsai_property_args)
        
        return args
    
    def _start_output_readers(self):
        """Start threads to read stdout and stderr in real-time."""
        self.stdout_data = []
        self.stderr_data = []
        
        def stdout_reader():
            for line in iter(self.bonsai_process.stdout.readline, ''):
                if line:
                    self.stdout_data.append(line.rstrip())
                    logging.info(f"Bonsai output: {line.rstrip()}")
            self.bonsai_process.stdout.close()
        
        def stderr_reader():
            for line in iter(self.bonsai_process.stderr.readline, ''):
                if line:
                    self.stderr_data.append(line.rstrip())
                    logging.error(f"Bonsai error: {line.rstrip()}")
            self.bonsai_process.stderr.close()
        
        self._output_threads = [
            threading.Thread(target=stdout_reader),
            threading.Thread(target=stderr_reader)
        ]
        
        for thread in self._output_threads:
            thread.daemon = True
            thread.start()
    
    def _assign_to_job_object(self):
        """Assign Bonsai process to Windows job object."""
        try:
            perms = win32con.PROCESS_TERMINATE | win32con.PROCESS_SET_QUOTA
            hProcess = win32api.OpenProcess(perms, False, self.bonsai_process.pid)
            win32job.AssignProcessToJobObject(self.hJob, hProcess)
            logging.info(f"Bonsai process {self.bonsai_process.pid} assigned to job object")
        except Exception as e:
            logging.warning(f"Failed to assign process to job object: {e}")
    
    def _monitor_bonsai(self):
        """Monitor the Bonsai process until it completes."""
        logging.info("Monitoring Bonsai process...")
        
        try:
            # Monitor process with memory usage checking
            self.process_monitor.monitor_process(
                self.bonsai_process,
                self._percent_used,
                kill_callback=self.kill_process
            )
            
            # Wait for output threads to finish
            for thread in self._output_threads:
                thread.join(timeout=2.0)
            
            # Check return code and log results
            return_code = self.bonsai_process.returncode
            if return_code != 0:
                logging.error(f"Bonsai exited with code: {return_code}")
                if self.stderr_data:
                    error_msg = "\n".join(self.stderr_data)
                    logging.error(f"Complete Bonsai error output:\n{error_msg}")
                logging.error(f"MID, {self.mouse_id}, UID, {self.user_id}, Action, Errored, "
                             f"Return_code, {return_code}")
            else:
                logging.info("Bonsai completed successfully")
                if self.stderr_data:
                    warning_msg = "\n".join(self.stderr_data)
                    logging.warning(f"Bonsai reported warnings:\n{warning_msg}")
                
                self.stop_time = datetime.datetime.now()
                duration_min = (self.stop_time - self.start_time).total_seconds() / 60.0
                logging.info(f"MID, {self.mouse_id}, UID, {self.user_id}, Action, Completed, "
                            f"Duration_min, {round(duration_min, 2)}")
        
        except Exception as e:
            logging.error(f"Error monitoring Bonsai process: {e}")
            self.stop()
    
    def kill_process(self):
        """Kill the Bonsai process immediately."""
        if self.bonsai_process and self.bonsai_process.poll() is None:
            logging.warning("Killing Bonsai process due to excessive memory usage")
            try:
                self.bonsai_process.kill()
                if WINDOWS_MODULES_AVAILABLE:
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.bonsai_process.pid)])
            except Exception as e:
                logging.error(f"Error killing Bonsai process: {e}")
    
    def stop(self):
        """Stop the Bonsai process if it's running."""
        if self.bonsai_process and self.bonsai_process.poll() is None:
            logging.info("Stopping Bonsai process...")
            
            try:
                # Try graceful termination first
                self.bonsai_process.terminate()
                
                # Wait for termination
                start_time = time.time()
                while time.time() - start_time < 3:
                    if self.bonsai_process.poll() is not None:
                        logging.info("Bonsai process terminated gracefully")
                        break
                    time.sleep(0.1)
                
                # Force kill if needed
                if self.bonsai_process.poll() is None:
                    logging.warning("Forcing kill of Bonsai process")
                    self.bonsai_process.kill()
                    
                    # Kill child processes on Windows
                    if WINDOWS_MODULES_AVAILABLE:
                        try:
                            subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.bonsai_process.pid)])
                        except Exception as e:
                            logging.warning(f"Could not kill child processes: {e}")
                    
            except Exception as e:
                logging.error(f"Error stopping Bonsai process: {e}")
    
    def get_bonsai_errors(self) -> str:
        """Return any errors reported by Bonsai."""
        if not self.stderr_data:
            return "No errors reported by Bonsai."
        return "\n".join(self.stderr_data)
    
    def cleanup(self):
        """Clean up resources when the script exits."""
        logging.info("Cleaning up resources...")
        self.stop()
    
    def signal_handler(self, sig, frame):
        """Handle Ctrl+C and other signals."""
        logging.info("Received signal to terminate")
        self.stop()
        sys.exit(0)
    
    def post_experiment_processing(self) -> bool:
        """
        Perform post-experiment processing specific to each rig type.
        This method should be overridden in each rig-specific launcher.
        
        Default implementation does nothing - each rig should implement
        its own data reformatting logic here.
        
        Returns:
            True if successful, False otherwise
        """
        logging.info("No post-experiment processing defined for this rig type")
        return True
    
    def _get_experiment_type_name(self) -> str:
        """
        Get the name of the experiment type for logging and error messages.
        
        Returns:
            String name of the experiment type (default: "Bonsai")
        """
        return "Bonsai"
    
    def run(self, param_file: Optional[str] = None) -> bool:
        """
        Run the experiment with the given parameters.
        
        Args:
            param_file: Path to the JSON parameter file
            
        Returns:
            True if successful, False otherwise
        """
        signal.signal(signal.SIGINT, self.signal_handler)
        
        try:
            # Load parameters
            self.load_parameters(param_file)
            
            # Set up repository
            if not self.git_manager.setup_repository(self.params):
                logging.error("Repository setup failed")
                return False
            
            # Start Bonsai
            self.start_bonsai()
              # Check for errors
            if self.bonsai_process.returncode != 0:
                logging.error(f"{self._get_experiment_type_name()} experiment failed")
                return False
            
            # Perform rig-specific post-processing            if not self.post_experiment_processing():
                logging.warning("Post-experiment processing failed, but experiment data was collected")
            
            return True
            
        except Exception as e:
            logging.exception(f"{self._get_experiment_type_name()} experiment failed: {e}")
            return False
        finally:
            self.stop()