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
import argparse
from typing import Dict, List, Optional, Any
from decimal import Decimal

# Import AIND data schema utilities for standardized folder naming
try:
    from aind_data_schema_models.data_name_patterns import build_data_name
    AIND_DATA_SCHEMA_AVAILABLE = True
except ImportError:
    AIND_DATA_SCHEMA_AVAILABLE = False
    logging.warning("aind-data-schema-models not available. Using fallback folder naming.")

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
from .bonsai_interface import BonsaiInterface


class BaseExperiment:
    """
    Base class for OpenScope experimental launchers.
    
    Provides core functionality for:
    - Parameter loading and management
    - Bonsai process management
    - Repository setup and version control
    - Process monitoring and memory management
    - Basic output file generation    """
    
    def __init__(self):
        """Initialize the base experiment with core functionality."""
        self.platform_info = self._get_platform_info()
        self.params = {}
        self.bonsai_process = None
        self.start_time = None
        self.stop_time = None
        self.config = {}
        
        # Session tracking variables
        self.subject_id = ""
        self.user_id = ""
        self.session_uuid = ""
        self.session_directory = ""  # Store the session output directory
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
        self.bonsai_interface = BonsaiInterface()
        
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
        if not self.params.get("subject_id"):
            try:
                subject_id = input("Enter subject ID (default: test_subject): ").strip()
                if not subject_id:
                    subject_id = "test_subject"
            except (EOFError, OSError):
                # Handle cases where input is not available (e.g., during testing)
                subject_id = "test_subject"
            runtime_info["subject_id"] = subject_id
          # Only collect user_id if not already provided in params
        if not self.params.get("user_id"):
            try:
                user_id = input("Enter user ID (default: test_user): ").strip()
                if not user_id:
                    user_id = "test_user"
            except (EOFError, OSError):
                # Handle cases where input is not available (e.g., during testing)
                user_id = "test_user"
            runtime_info["user_id"] = user_id
        
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
        runtime_info = self.collect_runtime_information()        # Update parameters with runtime information
        self.params.update(runtime_info)
        
        # Load hardware configuration
        self.config = self.config_loader.load_config(self.params)
        
        # Extract subject_id and user_id (using runtime info and config as fallbacks)
        self.subject_id = (
            self.params.get("subject_id") or 
            (self.config.get("Behavior", {}).get("subject_id") if self.config else "") or
            ""
        )
        self.user_id = (
            self.params.get("user_id") or
            (self.config.get("Behavior", {}).get("user_id") if self.config else "") or
            ""
        )
        
        logging.info(f"Using subject_id: {self.subject_id}, user_id: {self.user_id}")
    
    def start_bonsai(self):
        """Start the Bonsai workflow using BonsaiInterface."""
        logging.info(f"Subject ID: {self.subject_id}, User ID: {self.user_id}, Session UUID: {self.session_uuid}")
        
        # Store current memory usage
        vmem = psutil.virtual_memory()
        self._percent_used = vmem.percent
        
        try:
            # Resolve all Bonsai paths relative to repository
            resolved_paths = self._resolve_bonsai_paths()
            
            # Create updated params with resolved paths
            bonsai_params = self.params.copy()
            bonsai_params.update(resolved_paths)
              # Setup Bonsai environment (including installation if needed)
            if not self.bonsai_interface.setup_bonsai_environment(bonsai_params):
                raise RuntimeError("Failed to setup Bonsai environment")
            
            # Get workflow path
            workflow_path = self._get_workflow_path()
            
            # Handle output directory generation (migrate from Bonsai GenerateRootLoggingPath)
            params_for_bonsai = self.params.get("bonsai_parameters", {})

            # Construct arguments using BonsaiInterface
            workflow_args = self.bonsai_interface.construct_workflow_arguments(params_for_bonsai)
            
            # Start workflow using BonsaiInterface
            self.bonsai_process = self.bonsai_interface.start_workflow(
                workflow_path=workflow_path,
                arguments=workflow_args,
                output_path=self.session_directory
            )
            
            # Create threads to read output streams
            self._start_output_readers()
              # Assign process to Windows job object if available
            if WINDOWS_MODULES_AVAILABLE and self.hJob:
                self._assign_to_job_object()
            
            self.start_time = datetime.datetime.now()
            logging.info(f"Bonsai started at {self.start_time}")
            
            # Log experiment start
            logging.info(f"MID, {self.subject_id}, UID, {self.user_id}, Action, Executing, "
                        f"Checksum, {self.script_checksum}, Json_checksum, {self.params_checksum}")
            
            # Monitor Bonsai process
            self._monitor_bonsai()
            
        except Exception as e:
            logging.error(f"Failed to start Bonsai: {e}")
            raise

    def _resolve_bonsai_paths(self) -> Dict[str, str]:
        """
        Resolve all Bonsai-related paths relative to the repository.
        
        Returns:
            Dictionary with resolved absolute paths for Bonsai components
        """
        repo_path = self.git_manager.get_repository_path(self.params)
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

    def _get_workflow_path(self) -> str:
        """Get the absolute path to the Bonsai workflow file."""
        bonsai_path = self.params.get('bonsai_path')
        if not bonsai_path:
            raise ValueError("No Bonsai workflow path specified in parameters")
        
        workflow_path = bonsai_path
        if not os.path.isabs(workflow_path):
            # Try to find workflow in repository
            repo_path = self.git_manager.get_repository_path(self.params)
            if repo_path:
                workflow_path = os.path.join(repo_path, bonsai_path)
        
        if not os.path.exists(workflow_path):
            raise FileNotFoundError(f"Workflow file not found: {workflow_path}")
        
        return workflow_path

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
                logging.error(f"MID, {self.subject_id}, UID, {self.user_id}, Action, Errored, "
                             f"Return_code, {return_code}")
            else:
                logging.info("Bonsai completed successfully")
                if self.stderr_data:
                    warning_msg = "\n".join(self.stderr_data)
                    logging.warning(f"Bonsai reported warnings:\n{warning_msg}")
                
                self.stop_time = datetime.datetime.now()
                duration_min = (self.stop_time - self.start_time).total_seconds() / 60.0
                logging.info(f"MID, {self.subject_id}, UID, {self.user_id}, Action, Completed, "
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
        self.stop_time = datetime.datetime.now()
        
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
        
        # Finalize logging to flush all logs and close handlers
        self.finalize_logging()
    
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
            # Set start time
            self.start_time = datetime.datetime.now()
            
            # Load parameters
            self.load_parameters(param_file)
            
            # Set up repository
            if not self.git_manager.setup_repository(self.params):
                logging.error("Repository setup failed")
                return False
              # Determine output directory for data saving
            output_directory = self.determine_session_directory()
            self.session_directory = output_directory  # Store for post-processing
            
            # Set up continuous logging to output directory
            if output_directory:
                centralized_log_dir = self.params.get("centralized_log_directory")
                self.setup_continuous_logging(output_directory, centralized_log_dir)
                
                # Save experiment metadata after logging is set up
                self.save_experiment_metadata(output_directory, param_file)
            
            # Start Bonsai
            self.start_bonsai()
            
            # Check for errors
            if self.bonsai_process.returncode != 0:
                logging.error(f"{self._get_experiment_type_name()} experiment failed")
                return False
            
            # Perform rig-specific post-processing
            if not self.post_experiment_processing():
                logging.warning("Post-experiment processing failed, but experiment data was collected")
            
            return True
            
        except Exception as e:
            logging.exception(f"{self._get_experiment_type_name()} experiment failed: {e}")
            return False
        finally:
            self.stop()
    
    def determine_session_directory(self) -> Optional[str]:
        """
        Determine or generate output directory path using AIND data schema standards.

        Args:
            None
            
        Returns:
            Full path to the output directory, or None if not determinable
        """
        try:
           
            # Check if OutputFolder is already specified
            if "OutputFolder" in self.params:
                output_dir = self.params["OutputFolder"]
                logging.info(f"Using OutputFolder from parameters: {output_dir}")
            else:
                logging.error("OutputFolder not specified in parameters")
                raise ValueError("OutputFolder not specified in parameters")

            subject_id = self.subject_id

            # At this point, we should have root_folder and subject_id to generate a directory
            if subject_id is None:
                logging.error("Cannot generate output directory: missing root_folder or subject_id")
                raise ValueError("Missing subject_id")
            
            # Generate directory using AIND data schema standards
            date_time_offset = datetime.datetime.now()
            
            if AIND_DATA_SCHEMA_AVAILABLE:
                try:
                    # Use AIND standard naming: {subject_id}_{datetime}
                    folder_name = build_data_name(
                        label=subject_id,
                        creation_datetime=date_time_offset
                    )
                    logging.info(f"Generated AIND-compliant folder name: {folder_name}")
                except Exception as e:
                    logging.warning(f"Failed to use AIND data schema naming, falling back to default: {e}")
                    # Fallback to default naming
                    folder_name = f"{subject_id}_{date_time_offset.strftime('%Y-%m-%d_%H-%M-%S')}"
            else:
                # Fallback naming when AIND data schema is not available
                folder_name = f"{subject_id}_{date_time_offset.strftime('%Y-%m-%d_%H-%M-%S')}"
                logging.info(f"Using fallback folder name: {folder_name}")
            
            # We also assign the session UUID to the output directory
            self.session_uuid = folder_name

            # Create full output directory path
            output_dir = os.path.join(output_dir, folder_name)
            
            # Create the directory if it doesn't exist
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                logging.info(f"Created output directory: {output_dir}")
            else:
                logging.info(f"Output directory already exists: {output_dir}")
                
            return output_dir
            
        except Exception as e:
            logging.error(f"Failed to determine/generate output directory: {e}")
            return None
    
    def save_experiment_metadata(self, output_directory: str, param_file: Optional[str] = None):
        """
        Save experiment metadata to the output directory.
        
        This includes:
        - Original parameter JSON file
        - Command line arguments used to run the experiment
        - Runtime information and system details
        - Experiment logs (if available)
        
        Args:
            output_directory: Directory where metadata should be saved
            param_file: Path to the original parameter file (if available)
        """
        try:
            # Create metadata directory if it doesn't exist
            metadata_dir = os.path.join(output_directory, "experiment_metadata")
            os.makedirs(metadata_dir, exist_ok=True)
            
            # 1. Save original parameter file if provided
            if param_file and os.path.exists(param_file):
                param_filename = os.path.basename(param_file)
                param_dest = os.path.join(metadata_dir, f"original_{param_filename}")
                shutil.copy2(param_file, param_dest)
                logging.info(f"Saved original parameter file to: {param_dest}")
            
            # 2. Save processed parameters (with resolved paths, etc.)
            processed_params_file = os.path.join(metadata_dir, "processed_parameters.json")
            with open(processed_params_file, 'w') as f:
                json.dump(self.params, f, indent=2, default=str)
            logging.info(f"Saved processed parameters to: {processed_params_file}")
            
            # 3. Save command line arguments
            cmdline_file = os.path.join(metadata_dir, "command_line_arguments.json")
            cmdline_info = {
                "command_line": " ".join(sys.argv),
                "arguments": sys.argv,
                "working_directory": os.getcwd(),
                "python_executable": sys.executable,
                "timestamp": datetime.datetime.now().isoformat()
            }
            with open(cmdline_file, 'w') as f:
                json.dump(cmdline_info, f, indent=2)
            logging.info(f"Saved command line info to: {cmdline_file}")
            
            # 4. Save runtime and system information
            runtime_file = os.path.join(metadata_dir, "runtime_information.json")
            runtime_info = self.collect_runtime_information()
            runtime_info.update({
                "session_uuid": self.session_uuid,
                "subject_id": self.subject_id,
                "user_id": self.user_id,
                "script_checksum": self.script_checksum,
                "params_checksum": self.params_checksum,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "platform_info": self.platform_info
            })
            with open(runtime_file, 'w') as f:
                json.dump(runtime_info, f, indent=2, default=str)
            logging.info(f"Saved runtime information to: {runtime_file}")

            logging.info(f"Experiment metadata saved to: {metadata_dir}")
            
        except Exception as e:
            logging.error(f"Failed to save experiment metadata: {e}")
    
    @classmethod
    def create_argument_parser(cls, description: str = None) -> argparse.ArgumentParser:
        """
        Create a standard argument parser for experiment launchers.
        
        Args:
            description: Description for the argument parser
            
        Returns:
            Configured ArgumentParser instance
        """
        if description is None:
            description = f"Launch {cls.__name__} experiment"
            
        parser = argparse.ArgumentParser(description=description)
        parser.add_argument(
            'param_file',
            nargs='?',
            help='Path to the JSON parameter file. If not provided, will look for default parameter files.'
        )

        return parser
    
    @classmethod
    def run_from_args(cls, args: argparse.Namespace) -> int:
        """
        Run the experiment from parsed command line arguments.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        # Set up basic logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        try:
            # Validate parameter file if provided
            if args.param_file and not os.path.exists(args.param_file):
                logging.error(f"Parameter file not found: {args.param_file}")
                return 1
            
            # Create experiment instance
            experiment = cls()
            
            # Run the experiment
            experiment_name = cls.__name__.replace('Experiment', '').replace('Launcher', '')
            logging.info(f"Starting {experiment_name} with parameters: {args.param_file}")
            
            success = experiment.run(args.param_file)
            
            if success:
                logging.info(f"===== {experiment_name.upper()} COMPLETED SUCCESSFULLY =====")               
                return 0
            else:
                logging.error(f"===== {experiment_name.upper()} FAILED =====")
                logging.error("Check the logs above for error details.")
                return 1
                
        except KeyboardInterrupt:
            logging.info("Experiment interrupted by user")
            return 1
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            return 1
    
    @classmethod
    def main(cls, description: str = None, args: List[str] = None) -> int:
        """
        Main entry point for experiment launchers.
        
        Args:
            description: Description for the argument parser
            args: Command line arguments (defaults to sys.argv)
            
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        parser = cls.create_argument_parser(description)
        parsed_args = parser.parse_args(args)
        return cls.run_from_args(parsed_args)
    
    def setup_continuous_logging(self, output_directory: str, centralized_log_dir: Optional[str] = None):
        """
        Set up continuous logging to output directory and optionally centralized location.
        
        Args:
            output_directory: Directory where experiment-specific logs should be saved
            centralized_log_dir: Optional centralized logging directory
        """
        try:            # Create log filename with timestamp and session info
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            subject_id = self.params.get('subject_id')
            log_filename = f"experiment_{self.session_uuid}.log"
            
            # Set up logging format
            log_format = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # Get root logger
            root_logger = logging.getLogger()
            
            # 1. Set up file handler for output directory
            output_log_path = os.path.join(output_directory, log_filename)
            os.makedirs(os.path.dirname(output_log_path), exist_ok=True)
            
            output_handler = logging.FileHandler(output_log_path)
            output_handler.setLevel(logging.DEBUG)
            output_handler.setFormatter(log_format)
            root_logger.addHandler(output_handler)
            
            logging.info(f"Continuous logging started: {output_log_path}")
            
            # 2. Set up centralized logging if specified
            if centralized_log_dir:
                # Create centralized log directory structure: YYYY/MM/DD/
                date_path = datetime.datetime.now().strftime('%Y/%m/%d')
                centralized_dir = os.path.join(centralized_log_dir, date_path)
                os.makedirs(centralized_dir, exist_ok=True)
                
                centralized_log_path = os.path.join(centralized_dir, log_filename)
                
                centralized_handler = logging.FileHandler(centralized_log_path)
                centralized_handler.setLevel(logging.DEBUG)  # Slightly higher level for centralized
                centralized_handler.setFormatter(log_format)
                root_logger.addHandler(centralized_handler)
                
                logging.info(f"Centralized logging started: {centralized_log_path}")
            
            # 3. Set up console handler if not already present
            if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
                console_handler = logging.StreamHandler()
                console_handler.setLevel(logging.DEBUG)
                console_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
                root_logger.addHandler(console_handler)
            
            # Set overall logging level
            root_logger.setLevel(logging.DEBUG)
            
            # Log session information
            logging.info("="*60)
            logging.info("EXPERIMENT SESSION STARTED")
            logging.info(f"Session UUID: {self.session_uuid}")
            logging.info(f"Subject ID: {subject_id}")
            logging.info(f"User ID: {self.user_id}")
            logging.info(f"Platform: {self.platform_info}")
            logging.info(f"Output Directory: {output_directory}")
            if centralized_log_dir:
                logging.info(f"Centralized Logs: {centralized_log_dir}")
            logging.info("="*60)
            
        except Exception as e:
            print(f"Failed to set up continuous logging: {e}")
            # Continue without file logging - at least console will work

    def finalize_logging(self):
        """
        Finalize logging at the end of the experiment.
        
        Logs final session information and closes file handlers.
        """
        try:
            # Log final session information
            logging.info("="*60)
            logging.info("EXPERIMENT SESSION COMPLETED")
            logging.info(f"Session UUID: {self.session_uuid}")
            logging.info(f"Start Time: {self.start_time}")
            logging.info(f"Stop Time: {self.stop_time}")
            if self.start_time and self.stop_time:
                duration = self.stop_time - self.start_time
                logging.info(f"Duration: {duration}")
            logging.info(f"Final Memory Usage: {psutil.virtual_memory().percent}%")
            logging.info("="*60)
            
            # Close and remove file handlers to ensure logs are flushed
            root_logger = logging.getLogger()
            handlers_to_remove = []
            
            for handler in root_logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
                    handlers_to_remove.append(handler)
            
            for handler in handlers_to_remove:
                root_logger.removeHandler(handler)
                
        except Exception as e:
            print(f"Error finalizing logging: {e}")