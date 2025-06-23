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
import psutil
import json
import argparse
import subprocess
import threading
from typing import Dict, List, Optional, Any
from decimal import Decimal

# Import AIND data schema utilities for standardized folder naming
try:
    from aind_data_schema_models.data_name_patterns import build_data_name
    from aind_data_schema.core.session import Session, Stream, StimulusModality, Modality
    from aind_data_schema.components.devices import Software
    from aind_data_schema_models.modalities import Modality as StreamModality
    AIND_DATA_SCHEMA_AVAILABLE = True
except ImportError:
    AIND_DATA_SCHEMA_AVAILABLE = False
    logging.warning("aind-data-schema-models not available. Using fallback folder naming.")

from ..utils import rig_config
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
    
    def __init__(self, param_file: Optional[str] = None, rig_config_path: Optional[str] = None):
        """
        Initialize the base launcher with core functionality.
        
        Args:
            param_file: Path to JSON file containing experiment-specific parameters.
                       If None, only rig config and runtime prompts will be used.
            rig_config_path: Optional override path to rig config file. 
                           **ONLY use this for special cases like testing or non-standard setups.**
                           In normal operation, leave this as None to use the default rig config location.
        """
        self.platform_info = self._get_platform_info()
        self.params = {}
        self.start_time = None
        self.stop_time = None
        self.config = {}
        
        # Session tracking variables
        self.subject_id = ""
        self.user_id = ""
        self.session_uuid = ""
        self.output_session_folder = ""  # Store the session output directory      
        self.experiment_notes = ""  # Store experiment notes collected at the end
        self.animal_weight_prior = None  # Store animal weight prior collected at start
        
        # Process management (common to all interfaces)
        self.process = None
        self.stdout_data = []
        self.stderr_data = []
        self._output_threads = []
        self._percent_used = None        # Logging state
        self._logging_finalized = False  # Flag to prevent duplicate logging
        
        # Initialize launcher by loading all required configuration and data
        # This performs three key initialization steps:
        # 1. Loads experiment parameters from JSON file (if provided)
        # 2. Loads rig-specific configuration from TOML file  
        # 3. Collects any missing runtime information from user prompts
          # Step 1: Load experiment parameters from JSON file
        # Store original input parameters for metadata saving
        self.original_param_file = param_file
        self.original_input_params = {}
        
        if param_file:
            with open(param_file, 'r') as f:
                self.params = json.load(f)
                self.original_input_params = self.params.copy()  # Store original before merging
                logging.info(f"Loaded experiment parameters from {param_file}")
        else:
            logging.warning("No parameter file provided, using default parameters")
            self.params = {}
        
        # Step 2: Load rig configuration  
        self.rig_config = rig_config.get_rig_config(rig_config_path)
        
        # Step 3: Merge rig_config into params with proper priority
        # rig_config provides defaults, params (from JSON) override rig_config
        merged_params = dict(self.rig_config)  # Start with rig_config as base
        merged_params.update(self.params)      # Override with experiment-specific params
        self.params = merged_params
        
        # Step 4: Collect runtime information (only for missing values)
        runtime_info = self.collect_runtime_information()
        self.params.update(runtime_info)       # Runtime info has highest priority
        
        # Extract subject_id and user_id from params
        self.subject_id = self.params.get("subject_id", "")
        self.user_id = self.params.get("user_id", "")
        logging.info(f"Using subject_id: {self.subject_id}, user_id: {self.user_id}")
        logging.info(f"Using rig: {self.rig_config['rig_id']}")
        
        logging.info("BaseLauncher initialized")
    
    def _get_platform_info(self) -> Dict[str, Any]:
        """Get system and version information."""
        return {
            "python": sys.version.split()[0],
            "os": (platform.system(), platform.release(), platform.version()),
            "hardware": (platform.processor(), platform.machine()),
            "computer_name": platform.node(),
        }
    
    def collect_runtime_information(self) -> Dict[str, str]:
        """
        Collect key information from user at runtime (beginning of experiment).
        
        This method collects essential experiment information at the start:
        - Subject ID
        - User ID  
        
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

    def collect_end_experiment_information(self) -> Dict[str, str]:
        """
        Collect information from user at the end of the experiment.
        
        This method collects experiment wrap-up information:
        - Final experiment notes
        
        This method can be extended in derived classes to collect 
        rig-specific post-experiment information.
        
        Returns:
            Dictionary containing collected end-of-experiment information
        """
        end_info = {}
        
        try:
            print("\n" + "="*60)
            print("EXPERIMENT COMPLETED - Please provide final information")
            print("="*60)
            
            # Collect final experiment notes
            final_notes = input("Enter final experiment notes/observations (optional): ").strip()
            if final_notes:
                end_info["final_notes"] = final_notes
                self.experiment_notes = final_notes  # Store for session.json
            
        except (EOFError, OSError):
            # Handle cases where input is not available (e.g., during testing)
            logging.info("End-of-experiment information collection skipped (no interactive input available)")
            pass
        
        logging.info(f"Collected end-of-experiment info - {end_info}")
        return end_info
    
    def determine_output_session_folder(self) -> Optional[str]:
        """
        Determine the session output directory.
        
        Uses output_root_folder from params (which includes rig_config with proper override),
        then creates a session-specific subdirectory with subject_id and timestamp.
        
        Returns:
            Full path to the session folder where experiment data will be saved
        """
        try:
            # Get output_root_folder from params (already merged from rig_config with proper priority)
            output_root_folder = self.params.get("output_root_folder", os.getcwd())
            logging.info(f"Using output_root_folder: {output_root_folder}")

            # Validate subject_id is available
            if not self.subject_id:
                logging.error("Cannot generate session directory: missing subject_id")
                return None
            
            # Generate timestamped session folder name
            date_time_offset = datetime.datetime.now()
            
            if AIND_DATA_SCHEMA_AVAILABLE:
                try:
                    # Use AIND standard naming: {subject_id}_{datetime}
                    session_name = build_data_name(
                        label=self.subject_id,
                        creation_datetime=date_time_offset
                    )
                    logging.info(f"Generated AIND-compliant session name: {session_name}")
                except Exception as e:
                    logging.warning(f"Failed to use AIND data schema naming, falling back to default: {e}")
                    # Fallback to default naming
                    session_name = f"{self.subject_id}_{date_time_offset.strftime('%Y-%m-%d_%H-%M-%S')}"
            else:
                # Fallback naming when AIND data schema is not available
                session_name = f"{self.subject_id}_{date_time_offset.strftime('%Y-%m-%d_%H-%M-%S')}"
                logging.info(f"Using fallback session name: {session_name}")
            
            # Store session UUID for metadata
            self.session_uuid = session_name

            # Create full session folder path
            output_session_folder = os.path.join(output_root_folder, session_name)
            
            # Create the directory if it doesn't exist
            if not os.path.exists(output_session_folder):
                os.makedirs(output_session_folder)
                logging.info(f"Created output_session_folder: {output_session_folder}")
            else:
                logging.info(f"output_session_folder already exists: {output_session_folder}")
                
            return output_session_folder            
        except Exception as e:
            logging.error(f"Failed to determine output_session_folder: {e}")
            return None

    def save_launcher_metadata(self, output_directory: str):
        """
        Save launcher metadata to the output directory for experiment replication.
        
        This includes:
        - Original input parameters from the JSON file (input_parameters.json)
        - Fully processed parameters after merging rig config and runtime info (processed_parameters.json)
        - Command line arguments used to run the experiment
        - Runtime information and system details
        
        The processed_parameters.json file contains everything needed to replicate the experiment
        and can be used as input to a new launcher instance.
          Args:
            output_directory: Directory where metadata should be saved
        """
        try:
            # Create metadata directory if it doesn't exist
            metadata_dir = os.path.join(output_directory, "launcher_metadata")
            os.makedirs(metadata_dir, exist_ok=True)
            
            # 1. Save original input parameters from JSON file
            input_params_file = os.path.join(metadata_dir, "input_parameters.json")
            with open(input_params_file, 'w') as f:
                json.dump(self.original_input_params, f, indent=2, default=str)
            logging.info(f"Saved original input parameters to: {input_params_file}")
            
            # 2. Save processed parameters (merged rig config + input params + runtime info)
            # This is what you should use to replicate the experiment exactly
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
                "original_param_file": self.original_param_file,
                "timestamp": datetime.datetime.now().isoformat()
            }
            with open(cmdline_file, 'w') as f:
                json.dump(cmdline_info, f, indent=2)
            logging.info(f"Saved command line info to: {cmdline_file}")

            # 4. Save runtime and system information
            runtime_file = os.path.join(metadata_dir, "runtime_information.json")
            
            runtime_info = {
                "session_uuid": getattr(self, 'session_uuid', ''),
                "subject_id": getattr(self, 'subject_id', ''),
                "user_id": getattr(self, 'user_id', ''),
                "start_time": self.start_time.isoformat() if getattr(self, 'start_time', None) else None,
                "platform_info": getattr(self, 'platform_info', {})
            }
            with open(runtime_file, 'w') as f:
                json.dump(runtime_info, f, indent=2, default=str)
            logging.info(f"Saved runtime information to: {runtime_file}")

            logging.info(f"Launcher metadata saved to: {metadata_dir}")
            
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
            # Create log filename with session info
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
    
    @staticmethod
    def run_post_processing(session_directory: str) -> bool:
        """
        Pure post-processing method that works independently of launcher state.
        
        This static method performs post-processing based only on the session directory
        contents, without access to internal launcher state. This ensures that 
        post-processing can be run independently and enables experiment replication.
        
        Subclasses should override this method to implement rig-specific processing.
        
        Args:
            session_directory: Path to the session directory containing experiment data
            
        Returns:
            True if successful, False otherwise
        """
        logging.info(f"Running default post-processing for: {session_directory}")
        
        # Basic validation - check if directory exists
        if not os.path.exists(session_directory):
            logging.error(f"Session directory does not exist: {session_directory}")
            return False
            
        if not os.path.isdir(session_directory):
            logging.error(f"Path is not a directory: {session_directory}")
            return False
        
        # List contents for basic validation
        contents = os.listdir(session_directory)
        logging.info(f"Session directory contains {len(contents)} items")
        for item in contents:
            logging.debug(f"  - {item}")
        
        logging.info("Default post-processing completed successfully")
        return True
    
    def create_session_file(self, output_directory: str) -> bool:
        """
        Create session.json file with experiment metadata using aind-data-schema.
        
        This method creates a standardized session.json file in the output directory
        containing basic experiment metadata. Derived classes can override this method
        to add rig-specific metadata or use custom stimulus epoch and data stream builders.
        
        Args:
            output_directory: Directory where session.json should be created
              Returns:
            True if session.json was created successfully, False otherwise
        """
        try:
            # Check if aind-data-schema is available
            if not AIND_DATA_SCHEMA_AVAILABLE:
                logging.warning("aind-data-schema not available, skipping session.json creation")
                return False
            
            # Get rig_id from rig config (guaranteed to be available)
            rig_id = self.rig_config['rig_id']
            
            # --- Protocol and platform confirmation ---
            protocol_id = self.params.get("protocol_id")
            if protocol_id is not None:
                protocol_id = self._confirm_param("protocol_id", protocol_id)
            else:
                protocol_id = ["default_protocol"]  # Default value for tests
                
            iacuc_protocol = self.params.get("iacuc_protocol")
            if iacuc_protocol is not None:
                iacuc_protocol = self._confirm_param("iacuc_protocol", iacuc_protocol)
                
            mouse_platform_name = self.params.get("mouse_platform_name")
            if mouse_platform_name is not None:
                mouse_platform_name = self._confirm_param("mouse_platform_name", mouse_platform_name)
            else:
                mouse_platform_name = "default_platform"  # Default value for tests
                
            active_mouse_platform = self.params.get("active_mouse_platform")
            if active_mouse_platform is not None:
                active_mouse_platform = self._confirm_param("active_mouse_platform", active_mouse_platform)
            else:
                active_mouse_platform = True  # Default value for tests# --- Mouse runtime data collection ---
            collect_mouse_runtime_data = self.params.get("collect_mouse_runtime_data", False)
            animal_weight_prior = getattr(self, 'animal_weight_prior', None)
            animal_weight_post = None
              # Get stimulus epochs and data streams directly
            stimulus_epochs = self.get_stimulus_epochs()
            data_streams = self.get_data_streams(self.start_time, self.stop_time)

            # Prompt for animal_weight_post at end if enabled
            if collect_mouse_runtime_data:
                animal_weight_post = self._collect_mouse_runtime_data(at_start=False)

            # Create session object directly
            session = Session(
                experimenter_full_name=[self.user_id] if self.user_id else [],
                session_start_time=self.start_time,
                session_end_time=self.stop_time,
                session_type=self.params.get("session_type", "OpenScope experiment"),
                rig_id=rig_id,
                subject_id=self.subject_id,
                protocol_id=protocol_id,
                iacuc_protocol=iacuc_protocol,
                mouse_platform_name=mouse_platform_name,
                active_mouse_platform=active_mouse_platform,
                animal_weight_prior=animal_weight_prior,
                animal_weight_post=animal_weight_post,
                data_streams=data_streams,
                stimulus_epochs=stimulus_epochs,
                notes=self.experiment_notes
            )
            
            if session is None:
                logging.error("Failed to build session object")
                return False
            
            # Save session.json file
            session_file_path = os.path.join(output_directory, "session.json")
            with open(session_file_path, 'w') as f:
                json.dump(session.model_dump(), f, indent=2, default=str)
            
            logging.info(f"Session file created successfully: {session_file_path}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to create session.json file: {e}")
            return False

    
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
    
    def run(self) -> bool:
        """
        Run the experiment.
        
        This is the main orchestration method that should be called by
        interface-specific launchers. It handles the common workflow:
        1. Set up repository and output directories
        2. Set up logging
        3. Call start_experiment() (implemented by subclasses)
        4. Handle post-processing and cleanup
        
        Note: The launcher should already be initialized via __init__ before calling this method.
            
        Returns:
            True if successful, False otherwise
        """
        signal.signal(signal.SIGINT, self.signal_handler)
        
        try:
            # Set start time
            self.start_time = datetime.datetime.now()
            
            # Note: initialization now happens in __init__, not here
            
            # Collect animal weight prior at start if enabled
            self.animal_weight_prior = None
            if self.params.get("collect_mouse_runtime_data", False):
                self.animal_weight_prior = self._collect_mouse_runtime_data(at_start=True)
            
            # Set up repository
            if not git_manager.setup_repository(self.params):
                logging.error("Repository setup failed")
                return False            
            # Determine output_session_folder (specific directory where experiment data will be saved)
            output_session_folder = self.determine_output_session_folder()
            self.output_session_folder = output_session_folder  # Store for post-processing and interface use
            
            # Set up continuous logging to output_session_folder
            if output_session_folder:
                centralized_log_dir = self.params.get("centralized_log_directory")
                self.setup_continuous_logging(output_session_folder, centralized_log_dir)                  # Save launcher metadata after logging is set up
                self.save_launcher_metadata(output_session_folder)
            
            # Start the experiment (implemented by interface-specific launchers)
            if not self.start_experiment():
                logging.error(f"{self._get_launcher_type_name()} experiment failed to start")
                return False
            
            # Check for errors
            if not self.check_experiment_success():
                logging.error(f"{self._get_launcher_type_name()} experiment failed")
                return False
            
            # Collect end-of-experiment information (notes, outcome, etc.)
            self.collect_end_experiment_information()               
            
             # Perform rig-specific post-processing
            if not self.run_post_processing(self.output_session_folder):
                logging.warning("Post-experiment processing failed, but experiment data was collected")
                   
            if output_session_folder:
                self.create_session_file(output_session_folder)            

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
        logging.info(f"Subject ID: {self.subject_id}, User ID: {self.user_id}, Session UUID: {self.session_uuid}, Rig ID: {self.rig_config['rig_id']}")
        
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
            logging.info(f"Session UUID: {self.session_uuid} Starting.")
            
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

    def get_stimulus_epochs(self) -> list:
        """
        Get stimulus epochs for session creation.
        
        Base launcher has no stimulus epochs - these should be implemented in project-specific
        launchers based on the experimental protocol and Bonsai scripts used.
        
        Args:
            None
            
        Returns:
            Empty list (stimulus epochs should be defined in derived classes)
        """
        return []

    def get_data_streams(self, start_time: datetime.datetime, end_time: datetime.datetime) -> list:
        """
        Get data streams for session creation.
        
        Base launcher creates a data stream that refers to itself (the launcher).
        Subclasses can call super().get_data_streams() and extend the returned list
        with additional streams (e.g., Bonsai, Python scripts, MATLAB, etc.).
        
        Args:
            start_time: Session start time
            end_time: Session end time
              Returns:
            List containing launcher data stream
        """
        if not AIND_DATA_SCHEMA_AVAILABLE:
            return []
        
        # Create data stream for this launcher instance
        from openscope_experimental_launcher import __version__

        launcher_stream = Stream(
            stream_start_time=start_time,
            stream_end_time=end_time,
            stream_modalities=[StreamModality.BEHAVIOR],  # Launcher is behavioral control
            software=[Software(
                name=self.__class__.__name__,  # Use actual class name
                version=__version__,  # Package version
                url="https://github.com/AllenInstitute/openscope-experimental-launcher",  # GitHub repo
                parameters=self.params
            )]
        )
        return [launcher_stream]
    
    def _confirm_param(self, param_name, param_value):
        """Prompt user to confirm or edit a parameter value."""
        new_value = input(f"{param_name}: '{param_value}' (press Enter to keep, or type new value): ").strip()
        if not new_value:
            return param_value  # Keep the original value
        return new_value  # Use the new value

    def _get_valid_float(self, prompt, default=None):
        """Prompt user for a float value, with validation."""
        while True:
            val = input(f"{prompt} (grams, or leave blank for None): ").strip()
            if not val and default is not None:
                return default
            if not val:
                return None
            try:
                fval = float(val)
                if fval > 0:
                    return fval
                else:
                    print("Please enter a positive number.")
            except Exception:
                print("Invalid input. Please enter a number or leave blank.")

    def _collect_mouse_runtime_data(self, at_start=True):
        """Prompt for animal weight at start or end if enabled."""
        if at_start:
            return self._get_valid_float("Enter animal weight PRIOR to experiment")
        else:
            return self._get_valid_float("Enter animal weight POST experiment")
