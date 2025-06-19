"""
Base launcher class for OpenScope experiments.

This module contains the core functionality for launching experiments
with parameter management, session tracking, metadata collection, and logging.
Interface-specific functionality is delegated to separate interface modules.
"""

import os
import sys
import time
import signal
import logging
import datetime
import platform
import socket
import uuid
import hashlib
import atexit
import psutil
import shutil
import json
import argparse
import subprocess
import threading
from typing import Dict, List, Optional, Any
from decimal import Decimal

# Import AIND data schema utilities for standardized folder naming
try:
    from aind_data_schema_models.data_name_patterns import build_data_name
    AIND_DATA_SCHEMA_AVAILABLE = True
except ImportError:
    AIND_DATA_SCHEMA_AVAILABLE = False
    logging.warning("aind-data-schema-models not available. Using fallback folder naming.")

from ..utils import config_loader
from ..utils import git_manager


class BaseLauncher:
    """
    Base class for OpenScope experimental launchers.
    
    Provides core functionality for:
    - Parameter loading and management
    - Session tracking and metadata collection
    - Repository setup and version control
    - Output directory management
    - Logging setup and finalization
    - Process monitoring coordination
    
    Interface-specific functionality (Bonsai, MATLAB, Python) is handled
    by separate interface modules and launcher classes.
    """
    
    # Class variable to track cleanup registration
    _cleanup_registered = False
    
    def __init__(self):
        """Initialize the base launcher with core functionality."""
        self.platform_info = self._get_platform_info()
        self.params = {}
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
        
        # Process management (common to all interfaces)
        self.process = None
        self.stdout_data = []
        self.stderr_data = []
        self._output_threads = []
        self._percent_used = None
        
        # Logging state
        self._logging_finalized = False  # Flag to prevent duplicate logging
        
        # Register exit handlers only once per process, not per instance
        if not BaseLauncher._cleanup_registered:
            BaseLauncher._cleanup_registered = True
            # Use a class-level cleanup instead of instance cleanup
            def global_cleanup():
                # This will be called once at exit, not per instance
                pass
            atexit.register(global_cleanup)
            signal.signal(signal.SIGTERM, lambda sig, frame: sys.exit(0))
        
        logging.info("BaseLauncher initialized")
    
    def _get_platform_info(self) -> Dict[str, Any]:
        """Get system and version information."""
        return {
            "python": sys.version.split()[0],
            "os": (platform.system(), platform.release(), platform.version()),
            "hardware": (platform.processor(), platform.machine()),
            "computer_name": platform.node(),
            "rig_id": os.environ.get('RIG_ID', socket.gethostname()),
        }
    
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
        runtime_info = self.collect_runtime_information()
        # Update parameters with runtime information
        self.params.update(runtime_info)
        
        # Load hardware configuration
        self.config = config_loader.load_config(self.params)
        
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
    
    def determine_session_directory(self) -> Optional[str]:
        """
        Determine or generate output directory path using AIND data schema standards.

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
                logging.error("Cannot generate output directory: missing subject_id")
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
            runtime_info = {
                "session_uuid": self.session_uuid,
                "subject_id": self.subject_id,
                "user_id": self.user_id,
                "script_checksum": self.script_checksum,
                "params_checksum": self.params_checksum,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "platform_info": self.platform_info
            }
            with open(runtime_file, 'w') as f:
                json.dump(runtime_info, f, indent=2, default=str)
            logging.info(f"Saved runtime information to: {runtime_file}")

            logging.info(f"Experiment metadata saved to: {metadata_dir}")
            
        except Exception as e:
            logging.error(f"Failed to save experiment metadata: {e}")
    
    def setup_continuous_logging(self, output_directory: str, centralized_log_dir: Optional[str] = None):
        """
        Set up continuous logging to output directory and optionally centralized location.
        
        Args:
            output_directory: Directory where experiment-specific logs should be saved
            centralized_log_dir: Optional centralized logging directory
        """
        try:
            # Create log filename with timestamp and session info
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
        # Prevent duplicate finalization
        if self._logging_finalized:
            return
        
        self._logging_finalized = True
        
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
    
    def post_experiment_processing(self) -> bool:
        """
        Perform post-experiment processing specific to each rig type.
        This method should be overridden in each rig-specific launcher.
        
        Default implementation does nothing - each rig should implement
        its own data reformatting logic here.
        
        Returns:
            True if successful, False otherwise        """
        logging.info("No post-experiment processing defined for this launcher type")
        return True
    
    def _get_launcher_type_name(self) -> str:
        """
        Get the name of the launcher type for logging and error messages.
        
        This method should be overridden by interface-specific launchers.
        
        Returns:
            String name of the launcher type (default: "Generic")
        """
        return "Generic"
    
    def _get_script_path(self) -> str:
        """
        Get the absolute path to the script/workflow file.
        
        This method resolves the script_path parameter, handling both absolute
        and relative paths. For relative paths, it tries to resolve them relative
        to the repository path if available.
        
        Returns:
            Absolute path to the script/workflow file
            
        Raises:
            ValueError: If no script_path is specified in parameters
            FileNotFoundError: If the script file does not exist
        """
        script_path = self.params.get('script_path')
        if not script_path:
            raise ValueError("No script_path specified in parameters")
        
        resolved_path = script_path
        if not os.path.isabs(resolved_path):
            # Try to find script in repository
            repo_path = git_manager.get_repository_path(self.params)
            if repo_path:
                resolved_path = os.path.join(repo_path, script_path)
        
        if not os.path.exists(resolved_path):
            raise FileNotFoundError(f"Script file not found: {resolved_path}")
        
        return resolved_path
    
    def signal_handler(self, sig, frame):
        """Handle Ctrl+C and other signals."""
        logging.info("Received signal to terminate")
        self.stop()
        sys.exit(0)
    
    def stop(self):
        """
        Stop the experiment process if it's running.
        """
        self.stop_time = datetime.datetime.now()
        
        if self.process and self.process.poll() is None:
            logging.info(f"Stopping {self._get_launcher_type_name()} process...")
            
            try:
                # Try graceful termination first
                self.process.terminate()
                
                # Wait for termination
                start_time = datetime.datetime.now()
                while (datetime.datetime.now() - start_time).total_seconds() < 5:
                    if self.process.poll() is not None:
                        logging.info(f"{self._get_launcher_type_name()} process terminated gracefully")
                        break
                    time.sleep(0.1)
                
                # Force kill if needed
                if self.process.poll() is None:
                    logging.warning(f"Forcing kill of {self._get_launcher_type_name()} process")
                    self.process.kill()
                    
            except Exception as e:
                logging.error(f"Error stopping {self._get_launcher_type_name()} process: {e}")
        
        # Finalize logging to flush all logs and close handlers
        self.finalize_logging()
    
    def cleanup(self):
        """Clean up resources when the script exits."""
        logging.info("Cleaning up resources...")
        try:
            self.stop()
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
        return None
    
    def run(self, param_file: Optional[str] = None) -> bool:
        """
        Run the experiment with the given parameters.
        
        This is the main orchestration method that should be called by
        interface-specific launchers. It handles the common workflow:
        1. Set up parameters and session
        2. Set up repository and output directories
        3. Set up logging
        4. Call start_experiment() (implemented by subclasses)
        5. Handle post-processing and cleanup
        
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
            if not git_manager.setup_repository(self.params):
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
            
            # Start the experiment (implemented by interface-specific launchers)
            if not self.start_experiment():
                logging.error(f"{self._get_launcher_type_name()} experiment failed to start")
                return False
            
            # Check for errors
            if not self.check_experiment_success():
                logging.error(f"{self._get_launcher_type_name()} experiment failed")
                return False
              # Perform rig-specific post-processing
            if not self.post_experiment_processing():
                logging.warning("Post-experiment processing failed, but experiment data was collected")
            
            return True
            
        except Exception as e:
            logging.exception(f"{self._get_launcher_type_name()} experiment failed: {e}")
            return False
        finally:
            self.stop()
    
    def start_experiment(self) -> bool:
        """
        Start the experiment using the appropriate interface.
        
        This method creates and monitors a subprocess using the interface-specific
        process creation logic provided by create_process().
        
        Returns:
            True if experiment started successfully, False otherwise
        """
        logging.info(f"Subject ID: {self.subject_id}, User ID: {self.user_id}, Session UUID: {self.session_uuid}")
        
        # Store current memory usage for monitoring
        vmem = psutil.virtual_memory()
        self._percent_used = vmem.percent
        
        try:
            # Create the process using interface-specific logic
            self.process = self.create_process()
            
            # Check if process was created successfully
            if self.process is None:
                logging.error(f"Failed to create {self._get_launcher_type_name()} process")
                return False
            
            # Create threads to read output streams
            self._start_output_readers()
            
            # Log experiment start
            logging.info(f"MID, {self.subject_id}, UID, {self.user_id}, Action, Executing, "
                        f"Checksum, {self.script_checksum}, Json_checksum, {self.params_checksum}")
            
            # Monitor process
            self._monitor_process()
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to start {self._get_launcher_type_name()}: {e}")
            return False
    
    def create_process(self) -> subprocess.Popen:
        """
        Create the subprocess for the experiment.
        
        This method must be implemented by interface-specific launchers
        to create the appropriate subprocess (Bonsai, MATLAB, Python, etc.)
        
        Returns:
            subprocess.Popen object for the running process
        """
        raise NotImplementedError("create_process() must be implemented by interface-specific launchers")
    
    def check_experiment_success(self) -> bool:
        """
        Check if the experiment completed successfully.
        
        Returns:
            True if experiment completed successfully, False otherwise
        """
        # Check if process exists and has completed successfully
        if self.process and hasattr(self.process, 'returncode'):
            return self.process.returncode == 0
        return False
    
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
    
    def _start_output_readers(self):
        """Start threads to read stdout and stderr in real-time."""
        self.stdout_data = []
        self.stderr_data = []
        
        def stdout_reader():
            # Check if we're dealing with a Mock object (in tests)
            if hasattr(self.process.stdout, '_mock_name'):
                # For mock objects, just exit immediately to prevent infinite loops
                return
            
            try:
                for line in iter(self.process.stdout.readline, b''):
                    if line:
                        line_str = line.decode('utf-8').rstrip() if isinstance(line, bytes) else line.rstrip()
                        if line_str:  # Only log non-empty lines
                            self.stdout_data.append(line_str)
                            logging.info(f"{self._get_launcher_type_name()} output: {line_str}")
                    else:
                        break  # Exit if we get empty line
            except Exception as e:
                logging.debug(f"stdout reader error: {e}")
            finally:
                try:
                    self.process.stdout.close()
                except:
                    pass
        
        def stderr_reader():
            # Check if we're dealing with a Mock object (in tests)
            if hasattr(self.process.stderr, '_mock_name'):
                # For mock objects, just exit immediately to prevent infinite loops
                return
            
            try:
                for line in iter(self.process.stderr.readline, b''):
                    if line:
                        line_str = line.decode('utf-8').rstrip() if isinstance(line, bytes) else line.rstrip()
                        if line_str:  # Only log non-empty lines
                            self.stderr_data.append(line_str)
                            logging.error(f"{self._get_launcher_type_name()} error: {line_str}")
                    else:
                        break  # Exit if we get empty line
            except Exception as e:
                logging.debug(f"stderr reader error: {e}")
            finally:
                try:
                    self.process.stderr.close()
                except:
                    pass
        
        self._output_threads = [
            threading.Thread(target=stdout_reader),
            threading.Thread(target=stderr_reader)
        ]
        
        for thread in self._output_threads:
            thread.daemon = True
            thread.start()
    
    def _monitor_process(self):
        """Monitor the process until it completes."""
        logging.info(f"Monitoring {self._get_launcher_type_name()} process...")
        
        try:
            # Wait for process to complete
            self.process.wait()
            
            # Wait for output threads to finish
            for thread in self._output_threads:
                thread.join(timeout=2.0)
            
            # Check return code and log results
            return_code = self.process.returncode
            if return_code != 0:
                logging.error(f"{self._get_launcher_type_name()} exited with code: {return_code}")
                if self.stderr_data:
                    error_msg = "\n".join(self.stderr_data)
                    logging.error(f"Complete {self._get_launcher_type_name()} error output:\n{error_msg}")
                logging.error(f"MID, {self.subject_id}, UID, {self.user_id}, Action, Errored, "
                             f"Return_code, {return_code}")
            else:
                logging.info(f"{self._get_launcher_type_name()} completed successfully")
                if self.stderr_data:
                    warning_msg = "\n".join(self.stderr_data)
                    logging.warning(f"{self._get_launcher_type_name()} reported warnings:\n{warning_msg}")
                
                self.stop_time = datetime.datetime.now()
                duration_min = (self.stop_time - self.start_time).total_seconds() / 60.0
                logging.info(f"MID, {self.subject_id}, UID, {self.user_id}, Action, Completed, "
                            f"Duration_min, {round(duration_min, 2)}")
        
        except Exception as e:
            logging.error(f"Error monitoring {self._get_launcher_type_name()} process: {e}")
            self.stop()
    
    def get_process_errors(self) -> str:
        """Return any errors reported by the process."""
        if not self.stderr_data:
            return f"No errors reported by {self._get_launcher_type_name()}."
        return "\n".join(self.stderr_data)
