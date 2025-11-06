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
import psutil
import json
import subprocess
import threading
import importlib
from typing import Dict, Optional, Any

# Import AIND data schema utilities for standardized folder naming
try:
    from aind_data_schema_models.data_name_patterns import build_data_name
    AIND_DATA_SCHEMA_AVAILABLE = True
except ImportError:
    AIND_DATA_SCHEMA_AVAILABLE = False
    logging.warning("aind-data-schema-models not available. Using fallback folder naming.")

from ..utils import rig_config
from ..utils import git_manager
from ..utils import param_utils 
from .. import __version__



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
        self.param_file = param_file
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
        
        # Version tracking
        self._version = __version__
        
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

        # Step 1: Load rig configuration (provides defaults)
        self.rig_config = rig_config.get_rig_config(rig_config_path)

        # Step 2: Use param_utils to load parameters from file, merge with rig_config, and prompt for missing
        # Define required fields and defaults as needed for your workflow
        required_fields = ["subject_id", "user_id"]  # Add more as needed
        # Merge rig_config with explicit subject_id/user_id defaults
        defaults = dict(self.rig_config)
        defaults.setdefault("subject_id", "test_subject")
        defaults.setdefault("user_id", "test_user")
        help_texts = {"subject_id": "Animal or experiment subject ID", "user_id": "Experimenter user ID"}
        # Load parameters (file, overrides=None, required_fields, defaults, help_texts)
        self.params = param_utils.load_parameters(
            param_file=param_file,
            overrides=None,
            required_fields=required_fields,
            defaults=defaults,
            help_texts=help_texts
        )

        # Propagate any missing rig_config fields into params
        for k, v in self.rig_config.items():
            if k not in self.params:
                self.params[k] = v

        self.original_input_params = dict(self.params)  # Store for metadata

        # Extract subject_id and user_id from params (no fallback default needed)
        self.subject_id = self.params["subject_id"]
        self.user_id = self.params["user_id"]
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
        - Processed parameters after merging rig config (processed_parameters.json)
        - Command line arguments used to run the experiment
        
        The processed_parameters.json file contains only the input parameters 
        (after merging with rig config) and can be used as input to replicate 
        the experiment. Runtime information and launcher details are saved 
        in end_state.json instead.
        
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
            
            # 2. Save processed input parameters (original params + rig config)           
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
            # Create log filename in launcher_metadata directory
            subject_id = self.params.get('subject_id')
            log_filename = "launcher.log"
            
            # Set up logging format
            log_format = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # Get root logger
            root_logger = logging.getLogger()
            
            # 1. Set up file handler for launcher_metadata directory
            launcher_metadata_dir = os.path.join(output_directory, "launcher_metadata")
            os.makedirs(launcher_metadata_dir, exist_ok=True)
            output_log_path = os.path.join(launcher_metadata_dir, log_filename)
            
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
    
    def run_post_acquisition(self, param_file=None) -> bool:
        """Run post-acquisition pipeline using simplified entry schema.

        Entry dict format:
          {
            "module_type": "launcher_module" | "script_module",
            "module_path": "dotted.name" OR "relative/path/in/repo.py",
            "module_parameters": {key: value}
          }

        Plain string entries remain supported (treated as launcher_module).
        """
        if param_file is None:
            param_file = self.param_file
        # Prefer processed parameters if available
        processed_params_path = None
        if self.output_session_folder:
            candidate = os.path.join(self.output_session_folder, "launcher_metadata", "processed_parameters.json")
            if os.path.exists(candidate):
                processed_params_path = candidate
        if processed_params_path:
            params = param_utils.load_parameters(param_file=processed_params_path)
        else:
            params = param_utils.load_parameters(param_file=param_file)

        pipeline = params.get("post_acquisition_pipeline", [])
        all_success = True
        repo_path = git_manager.get_repository_path(params)
        session_folder = params.get("output_session_folder") or self.output_session_folder

        def _invoke_launcher_module(mod_name: str, merged_params: dict) -> bool:
            try:
                logging.info(f"Post-acquisition launcher module: {mod_name}")
                mod = importlib.import_module(f"openscope_experimental_launcher.post_acquisition.{mod_name}")
                func = None
                if hasattr(mod, "run_post_acquisition"):
                    func = getattr(mod, "run_post_acquisition")
                elif hasattr(mod, "run"):
                    func = getattr(mod, "run")
                else:
                    logging.warning(f"Module {mod_name} has no run_post_acquisition() or run(); skipping.")
                    return True
                result = func(param_file) if func.__code__.co_argcount == 1 else func(merged_params)
                return result in (None, 0, True)
            except Exception as e:
                logging.error(f"Launcher module error {mod_name}: {e}")
                return False

        def _invoke_script_module(path_in_repo: str, merged_params: dict) -> bool:
            try:
                if not repo_path:
                    raise RuntimeError("No repository path available for script_module")
                abs_path = os.path.join(repo_path, path_in_repo.replace('/', os.sep))
                if not os.path.isfile(abs_path):
                    raise FileNotFoundError(f"Script module file not found: {abs_path}")
                spec = importlib.util.spec_from_file_location("script_post_module", abs_path)
                if spec is None or spec.loader is None:
                    raise RuntimeError("Failed to build import spec for script module")
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[attr-defined]
                func_name = merged_params.get("function")
                func = None
                if func_name and hasattr(mod, func_name):
                    func = getattr(mod, func_name)
                elif hasattr(mod, "run_post_acquisition"):
                    func = getattr(mod, "run_post_acquisition")
                elif hasattr(mod, "run"):
                    func = getattr(mod, "run")
                else:
                    raise AttributeError("No callable entry point found (run_post_acquisition/run/function)")
                try:
                    if func.__code__.co_argcount == 1:
                        result = func(merged_params)
                    else:
                        result = func()
                except Exception as inner_e:
                    logging.error(f"Error invoking script module function: {inner_e}")
                    return False
                return result in (None, 0, True)
            except Exception as e:
                logging.error(f"Script module error {path_in_repo}: {e}")
                return False

        for raw_entry in pipeline:
            if isinstance(raw_entry, str):
                entry = {"module_type": "launcher_module", "module_path": raw_entry, "module_parameters": {}}
            elif isinstance(raw_entry, dict):
                entry = raw_entry
            else:
                logging.warning(f"Ignoring unsupported pipeline entry: {raw_entry}")
                continue
            module_type = entry.get("module_type", "launcher_module")
            module_path = entry.get("module_path")
            module_params = entry.get("module_parameters", {}) or {}
            merged = dict(params)
            merged.update(module_params)
            if session_folder:
                merged.setdefault("output_session_folder", session_folder)
            if module_type == "launcher_module":
                ok = _invoke_launcher_module(module_path, merged)
            elif module_type == "script_module":
                ok = _invoke_script_module(module_path, merged)
            else:
                logging.warning(f"Unknown module_type '{module_type}' in post-acquisition entry")
                continue
            if not ok:
                all_success = False
                logging.error(f"Post-acquisition step failed: {module_path}")
            else:
                logging.info(f"Post-acquisition step completed: {module_path}")

        if all_success:
            logging.info("All post-acquisition steps completed successfully.")
        else:
            logging.warning("Some post-acquisition steps failed. Check logs for details.")
        return all_success
       
    
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
    
    def _start_resource_logging(self, session_folder: str, acquisition_pid: Optional[int] = None):
        """Start a background thread to log resource usage for launcher and subprocess."""
        # Place resource_usage.json in launcher_metadata directory inside session_folder
        launcher_metadata_dir = os.path.join(session_folder, "launcher_metadata")
        os.makedirs(launcher_metadata_dir, exist_ok=True)
        self._resource_log_file = os.path.join(launcher_metadata_dir, "resource_usage.json")
        self._resource_log_stop = threading.Event()
        self._resource_log_data = []
        interval = self.params.get("resource_log_interval", 5)
        def log_loop():
            import psutil, datetime, json, time
            launcher_proc = psutil.Process(os.getpid())
            acq_proc = None
            if acquisition_pid:
                try:
                    acq_proc = psutil.Process(acquisition_pid)
                except Exception:
                    acq_proc = None
            while not self._resource_log_stop.is_set():
                entry = {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "launcher": {
                        "cpu_percent": launcher_proc.cpu_percent(interval=None),
                        "memory_mb": launcher_proc.memory_info().rss / 1024 / 1024,
                    },
                }
                if acq_proc:
                    try:
                        entry["acquisition"] = {
                            "cpu_percent": acq_proc.cpu_percent(interval=None),
                            "memory_mb": acq_proc.memory_info().rss / 1024 / 1024,
                        }
                    except (psutil.NoSuchProcess, ProcessLookupError):
                        entry["acquisition"] = None
                        acq_proc = None
                    except Exception:
                        entry["acquisition"] = None
                else:
                    entry["acquisition"] = None
                self._resource_log_data.append(entry)
                with open(self._resource_log_file, "w") as f:
                    json.dump(self._resource_log_data, f, indent=2)
                time.sleep(interval)
        self._resource_log_thread = threading.Thread(target=log_loop, daemon=True)
        self._resource_log_thread.start()

    def _stop_resource_logging(self):
        if hasattr(self, '_resource_log_stop'):
            self._resource_log_stop.set()
        if hasattr(self, '_resource_log_thread') and self._resource_log_thread:
            self._resource_log_thread.join(timeout=2)

    def run(self) -> bool:
        """
        Run the experiment.
        
        This is the main orchestration method that should be called by
        interface-specific launchers. It handles the common workflow:
        1. Set up repository and output directories
        2. Set up logging
        3. Call start_experiment() (implemented by subclasses)
        4. Handle post-acquisition and cleanup
        
        Note: The launcher should already be initialized via __init__ before calling this method.
            
        Returns:
            True if successful, False otherwise
        """
        signal.signal(signal.SIGINT, self.signal_handler)

        try:
            self.start_time = datetime.datetime.now()

            # Set up repository
            if not git_manager.setup_repository(self.params):
                logging.error("Repository setup failed")
                return False

            # Set up output session folder
            output_session_folder = self.determine_output_session_folder()
            self.output_session_folder = output_session_folder
            self.params["output_session_folder"] = output_session_folder

            # Set up logging and metadata
            if output_session_folder:
                centralized_log_dir = self.params.get("centralized_log_directory")
                self.setup_continuous_logging(output_session_folder, centralized_log_dir)
                self.save_launcher_metadata(output_session_folder)
                # Start resource logging (launcher only for now)
                # Start resource logging only if enabled in params (must be explicitly True)
                if self.params.get("resource_log_enabled") is True:
                    self._start_resource_logging(output_session_folder, acquisition_pid=None)

            # Run pre-acquisition steps
            if not self.run_pre_acquisition():
                logging.warning("Pre-acquisition processing failed, but continuing with experiment.")

            # Start the experiment (implemented by interface-specific launchers)
            experiment_success = self.start_experiment()

            # Update resource logger to include acquisition PID
            if self.process is not None:
                try:
                    self._stop_resource_logging()
                    self._start_resource_logging(output_session_folder, acquisition_pid=self.process.pid)
                except Exception as e:
                    logging.warning(f"Could not update resource logger with acquisition PID: {e}")

            if not experiment_success:
                logging.error(f"{self._get_launcher_type_name()} experiment failed to start")
                return False

            # Check for errors
            if not self.check_experiment_success():
                logging.error(f"{self._get_launcher_type_name()} experiment failed")
                return False

            # Save end state for post-acquisition tools
            self.save_end_state(self.output_session_folder)

            # Run post-acquisition steps
            if not self.run_post_acquisition():
                logging.warning("Post-acquisition processing failed, but experiment data was collected")

            return True

        except Exception as e:
            if hasattr(self, 'output_session_folder') and self.output_session_folder:
                self.save_debug_state(self.output_session_folder, e)
            logging.exception(f"{self._get_launcher_type_name()} experiment failed: {e}")
            return False

        finally:
            self._stop_resource_logging()
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
        Create a dummy subprocess for testing: runs a brief 'hello world' command.
        Returns:
            subprocess.Popen object for the running process, or None if not implemented.
        """
        import subprocess
        import sys
        # Use a cross-platform hello world command
        if sys.platform.startswith('win'):
            cmd = [sys.executable, '-c', 'print("Hello from BaseLauncher!")']
        else:
            cmd = [sys.executable, '-c', 'print(\"Hello from BaseLauncher!\")']
        try:
            return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            logging.error(f"Failed to start dummy hello world process: {e}")
            return None
    
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
    def run_from_params(cls, param_file):
        """
        Run the experiment with the specified parameters.
        
        Args:
            param_file: Path to the JSON parameter file
            
        Returns:
            True if successful, False otherwise
        """
        # Set up basic logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        try:
            # Validate parameter file
            if param_file and not os.path.exists(param_file):
                logging.error(f"Parameter file not found: {param_file}")
                return False
            
            # Create launcher instance with parameter file
            launcher = cls(param_file=param_file)
            
            # Run the launcher
            logging.info(f"Starting {cls.__name__} with parameters: {param_file}")
            
            success = launcher.run()
            
            if success:
                logging.info(f"===== {cls.__name__.upper()} COMPLETED SUCCESSFULLY =====")               
                return True
            else:
                logging.error(f"===== {cls.__name__.upper()} FAILED =====")
                logging.error("Check the logs above for error details.")
                return False
                
        except KeyboardInterrupt:
            logging.info("Launcher interrupted by user")
            return False
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            return False
    
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

    def save_end_state(self, output_directory: str) -> bool:
        """
        Save end-of-experiment state for post-acquisition tools.
        
        This saves essential runtime information that post-acquisition tools need,
        such as session creation. The data is saved in a simple JSON format that
        can be easily read by post-acquisition scripts.
          Args:
            output_directory: Directory where end_state.json should be created
            
        Returns:
            True if end state was saved successfully, False otherwise
        """
        try:
            # Create metadata directory if it doesn't exist
            metadata_dir = os.path.join(output_directory, "launcher_metadata")
            os.makedirs(metadata_dir, exist_ok=True)
            
            end_state_file = os.path.join(metadata_dir, "end_state.json")
            
            # Collect end state data
            end_state = {
                "launcher_info": {
                    "class_name": self.__class__.__name__,
                    "module": self.__class__.__module__,
                    "version": getattr(self, '_version', 'unknown')
                },
                "session_info": {
                    "subject_id": getattr(self, 'subject_id', None),
                    "user_id": getattr(self, 'user_id', None),
                    "session_uuid": getattr(self, 'session_uuid', None),
                    "start_time": self.start_time.isoformat() if hasattr(self, 'start_time') and self.start_time else None,
                    "stop_time": self.stop_time.isoformat() if hasattr(self, 'stop_time') and self.stop_time else None,
                },
                "experiment_data": {
                    "output_session_folder": getattr(self, 'output_session_folder', None),
                },
                "parameters": getattr(self, 'params', {}),
                "rig_config": getattr(self, 'rig_config', {}),
                "saved_at": datetime.datetime.now().isoformat()
            }
            
            # Allow subclasses to add custom end state data
            custom_end_state = self.get_custom_end_state()
            if custom_end_state:
                end_state["custom_data"] = custom_end_state
            
            # Write end state file
            with open(end_state_file, 'w') as f:
                json.dump(end_state, f, indent=2, default=str)
                
            logging.info(f"End state saved to: {end_state_file}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to save end state: {e}")
            return False
    
    def get_custom_end_state(self) -> Dict[str, Any]:
        """
        Get custom end state data from subclasses.
        
        Subclasses can override this method to add their own data to the end state file.
        This data will be available to post-acquisition tools.
        
        Returns:
            Dictionary of custom data to include in end state, or None if no custom data
        """
        return None
    
    def save_debug_state(self, output_directory: str, exception: Exception) -> bool:
        """
        Save debug state when an experiment crashes.
        
        This saves the complete launcher state at the time of crash for debugging purposes.
        Unlike end state, this includes all internal variables and is only created on errors.
        
        Args:
            output_directory: Directory where debug_state.json should be created
            exception: The exception that caused the crash
            
        Returns:
            True if debug state was saved successfully, False otherwise
        """
        try:
            # Create metadata directory if it doesn't exist
            metadata_dir = os.path.join(output_directory, "launcher_metadata")
            os.makedirs(metadata_dir, exist_ok=True)
            
            debug_state_file = os.path.join(metadata_dir, "debug_state.json")
            
            # Collect all accessible attributes for debugging
            debug_state = {
                "crash_info": {
                    "exception_type": type(exception).__name__,
                    "exception_message": str(exception),
                    "crash_time": datetime.datetime.now().isoformat()
                },
                "launcher_state": {},
                "system_info": {
                    "python_version": sys.version,
                    "platform": sys.platform,
                    "cwd": os.getcwd()
                }
            }
            
            # Collect all launcher attributes (for debugging)
            for attr_name in dir(self):
                if not attr_name.startswith('_') and not callable(getattr(self, attr_name)):
                    try:
                        value = getattr(self, attr_name)
                        # Try to serialize the value
                        json.dumps(value, default=str)  # Test serialization
                        debug_state["launcher_state"][attr_name] = value
                    except (TypeError, ValueError):
                        # If serialization fails, store type info instead
                        debug_state["launcher_state"][attr_name] = f"<non-serializable: {type(value).__name__}>"
                    except Exception:
                        # Skip attributes that cause other errors
                        debug_state["launcher_state"][attr_name] = "<error accessing attribute>"
            
            # Write debug state file
            with open(debug_state_file, 'w') as f:
                json.dump(debug_state, f, indent=2, default=str)
                
            logging.error(f"Debug state saved to: {debug_state_file}")
            return True
            
        except Exception as debug_e:
            logging.error(f"Failed to save debug state: {debug_e}")
            return False

    def run_pre_acquisition(self, param_file=None) -> bool:
        """Run pre-acquisition pipeline using simplified entry schema.

        New unified entry format (dict):
          {
            "module_type": "launcher_module" | "script_module",
            "module_path": "relative.dotted.name" OR "relative/path/in/repo.py",
            "module_parameters": {"key": "value", ...}  # optional
          }

        Backward compatibility:
          - Plain string entries are treated as launcher_module with module_path=string.

        Resolution rules:
          launcher_module -> import path: src.openscope_experimental_launcher.pre_acquisition.<module_path>
          script_module   -> loaded from cloned repository root joined with module_path (file path);
                             expects a callable `run_pre_acquisition(params_dict)` OR a function name
                             specified via module_parameters["function"]; if neither present uses
                             a default `run()` if available.

        The `module_parameters` dict is merged into base params and passed to the function.
        """
        if param_file is None:
            param_file = self.param_file
        params = param_utils.load_parameters(param_file=param_file)
        pipeline = params.get("pre_acquisition_pipeline", [])
        all_success = True
        repo_path = git_manager.get_repository_path(params)
        session_folder = params.get("output_session_folder") or self.output_session_folder

        def _invoke_launcher_module(mod_name: str, merged_params: dict) -> bool:
            try:
                logging.info(f"Pre-acquisition launcher module: {mod_name}")
                # Correct package import (no 'src.' prefix for runtime use)
                mod = importlib.import_module(f"openscope_experimental_launcher.pre_acquisition.{mod_name}")
                func = None
                if hasattr(mod, "run_pre_acquisition"):
                    func = getattr(mod, "run_pre_acquisition")
                elif hasattr(mod, "run"):
                    func = getattr(mod, "run")
                else:
                    logging.warning(f"Module {mod_name} has no run_pre_acquisition() or run(); skipping.")
                    return True
                result = func(param_file) if func.__code__.co_argcount == 1 else func(merged_params)
                return result in (None, 0, True)
            except Exception as e:
                logging.error(f"Launcher module error {mod_name}: {e}")
                return False

        def _invoke_script_module(path_in_repo: str, merged_params: dict) -> bool:
            try:
                if not repo_path:
                    raise RuntimeError("No repository path available for script_module")
                abs_path = os.path.join(repo_path, path_in_repo.replace('/', os.sep))
                if not os.path.isfile(abs_path):
                    # Fallback: try searching for the filename anywhere under repo_path
                    fallback = None
                    target_name = os.path.basename(path_in_repo)
                    for root, _dirs, files in os.walk(repo_path):
                        if target_name in files:
                            fallback = os.path.join(root, target_name)
                            break
                    if fallback and os.path.isfile(fallback):
                        abs_path = fallback
                    else:
                        raise FileNotFoundError(f"Script module file not found: {abs_path}")
                spec = importlib.util.spec_from_file_location("script_pre_module", abs_path)
                if spec is None or spec.loader is None:
                    raise RuntimeError("Failed to build import spec for script module")
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[attr-defined]
                func_name = merged_params.get("function")
                func = None
                if func_name and hasattr(mod, func_name):
                    func = getattr(mod, func_name)
                elif hasattr(mod, "run_pre_acquisition"):
                    func = getattr(mod, "run_pre_acquisition")
                elif hasattr(mod, "run"):
                    func = getattr(mod, "run")
                else:
                    raise AttributeError("No callable entry point found (run_pre_acquisition/run/function)")
                # Argument mapping for multi-arg legacy functions (e.g. generate_single_session_csv)
                try:
                    argcount = func.__code__.co_argcount
                    result = None
                    if argcount == 0:
                        result = func()
                    elif argcount == 1:
                        result = func(merged_params)
                    else:
                        # Build ordered args from common keys
                        import inspect
                        sig = inspect.signature(func)
                        ordered_args = []
                        for i, (p_name, p) in enumerate(sig.parameters.items()):
                            if p_name in ("params", "parameters") and argcount == 1:
                                ordered_args.append(merged_params)
                            elif p_name == "output_path" and "output_filename" in merged_params:
                                session_folder = merged_params.get("output_session_folder") or merged_params.get("output_root_folder")
                                ordered_args.append(os.path.join(session_folder, merged_params.get("output_filename")))
                            elif p_name == "session_type" and "session_type" in merged_params:
                                ordered_args.append(merged_params.get("session_type"))
                            elif p_name == "seed" and "seed" in merged_params:
                                ordered_args.append(merged_params.get("seed"))
                            else:
                                # Best-effort: pass None or default
                                if p.default is inspect._empty:
                                    ordered_args.append(None)
                                else:
                                    ordered_args.append(p.default)
                        result = func(*ordered_args)
                except Exception as inner_e:
                    logging.error(f"Error invoking script module function: {inner_e}")
                    return False
                return result in (None, 0, True)
            except Exception as e:
                logging.error(f"Script module error {path_in_repo}: {e}")
                return False

        for raw_entry in pipeline:
            # Legacy repo_module support
            if isinstance(raw_entry, dict) and raw_entry.get("type") == "repo_module":
                legacy_path = raw_entry.get("repo_relative_path")
                legacy_func = raw_entry.get("function")
                legacy_kwargs = raw_entry.get("kwargs", {})
                # Build merged params and include legacy function name so script module invoker can find it
                merged = dict(params)
                merged.update(legacy_kwargs or {})
                if session_folder:
                    merged.setdefault("output_session_folder", session_folder)
                if legacy_func:
                    merged.setdefault("function", legacy_func)
                ok = _invoke_script_module(legacy_path, merged)
                if not ok:
                    all_success = False
                    logging.error(f"Pre-acquisition legacy repo_module failed: {legacy_path}")
                else:
                    logging.info(f"Pre-acquisition legacy repo_module completed: {legacy_path}")
                continue  # move to next pipeline entry

            # Normalize simplified schema or plain string
            if isinstance(raw_entry, str):
                entry = {"module_type": "launcher_module", "module_path": raw_entry, "module_parameters": {}}
            elif isinstance(raw_entry, dict):
                entry = raw_entry
            else:
                logging.warning(f"Ignoring unsupported pipeline entry: {raw_entry}")
                continue

            module_type = entry.get("module_type", "launcher_module")
            module_path = entry.get("module_path")
            module_params = entry.get("module_parameters", {}) or {}
            merged = dict(params)
            merged.update(module_params)
            if session_folder:
                merged.setdefault("output_session_folder", session_folder)

            if module_type == "launcher_module":
                ok = _invoke_launcher_module(module_path, merged)
            elif module_type == "script_module":
                ok = _invoke_script_module(module_path, merged)
            else:
                logging.warning(f"Unknown module_type '{module_type}' in pre-acquisition entry")
                continue

            if not ok:
                all_success = False
                logging.error(f"Pre-acquisition step failed: {module_path}")
            else:
                logging.info(f"Pre-acquisition step completed: {module_path}")

        if all_success:
            logging.info("All pre-acquisition steps completed successfully.")
        else:
            logging.warning("Some pre-acquisition steps failed. Check logs for details.")
        return all_success

def run_from_params(param_file):
    """
    Module-level entry point for the unified launcher wrapper.
    Calls BaseLauncher.run_from_params.
    """
    return BaseLauncher.run_from_params(param_file)
