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
import importlib.util
import traceback

if os.name == "nt":  # pragma: no cover - Windows-specific imports
    try:
        import msvcrt
        import pywintypes
        import win32con
        import win32file
    except ImportError:  # pragma: no cover - fallback if pywin32 missing
        msvcrt = None
        pywintypes = None
        win32con = None
        win32file = None


class _PlaceholderDict(dict):
    """Format-friendly dict that leaves unknown keys untouched."""

    def __missing__(self, key: str) -> str:  # pragma: no cover - defensive formatting
        return "{" + key + "}"


class SharedFileHandler(logging.FileHandler):
    """File handler that keeps the log file shareable on Windows."""

    @staticmethod
    def _shared_supported() -> bool:
        return os.name == "nt" and all((msvcrt, win32con, win32file))

    def _open(self):
        if not self._shared_supported():  # pragma: no cover - non-Windows path
            return super()._open()

        share_flags = (
            win32con.FILE_SHARE_READ
            | win32con.FILE_SHARE_WRITE
            | win32con.FILE_SHARE_DELETE
        )
        creation_disposition = win32con.OPEN_ALWAYS if "a" in self.mode else win32con.CREATE_ALWAYS

        try:
            handle = win32file.CreateFile(
                self.baseFilename,
                win32con.GENERIC_WRITE,
                share_flags,
                None,
                creation_disposition,
                win32con.FILE_ATTRIBUTE_NORMAL,
                None,
            )
        except Exception:  # pragma: no cover - fallback when pywin32 unavailable
            return super()._open()

        raw_handle = None
        fd = None
        try:
            if "a" in self.mode:
                win32file.SetFilePointer(handle, 0, win32con.FILE_END)
            raw_handle = handle.Detach()
            fd = msvcrt.open_osfhandle(raw_handle, os.O_APPEND | os.O_WRONLY)
            return os.fdopen(
                fd,
                self.mode,
                buffering=-1,
                encoding=self.encoding,
                errors=getattr(self, "errors", None),
            )
        except Exception:
            if fd is not None:
                os.close(fd)
            if raw_handle is not None:
                win32file.CloseHandle(raw_handle)
            else:
                handle.Close()
            raise

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

        # Expand any {rig_param:<key>} placeholders in script_parameters generically
        self._expand_rig_param_placeholders()

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

    def _get_script_path(self) -> str:
        """Resolve and validate script_path parameter (generic for Python/Matlab)."""
        script_path = self.params.get('script_path')
        if not script_path:
            raise RuntimeError("Missing 'script_path' parameter")
        if os.path.isabs(script_path):
            candidate = script_path
        else:
            repo_root = git_manager.get_repository_path(self.params)
            candidate = os.path.join(repo_root, script_path) if repo_root else script_path
        if not os.path.isfile(candidate):
            raise RuntimeError(f"Script not found: {candidate}")
        return candidate

    def _expand_rig_param_placeholders(self):
        """Expand placeholders in script_parameters.

        Supported placeholder patterns:
        - {rig_param:<key>} -> substituted with self.params[<key>] (from merged params including rig_config)
        - {subject_id} -> substituted with self.params['subject_id'] (convenience shortcut)

        This allows param JSON files to declaratively map rig configuration fields (or any
        top-level param) into workflow script parameters without launcher-specific logic.

        Examples:
            "script_parameters": {"PortName": "{rig_param:COM_port}"}
            "script_parameters": {"Animal": "{subject_id}"}

        Unknown rig_param keys raise a RuntimeError to fail fast and surface misconfiguration.
        """
        script_parameters = self.params.get("script_parameters")
        if not script_parameters or not isinstance(script_parameters, dict):
            return
        import re
        rig_pattern = re.compile(r"\{rig_param:([^}]+)\}")
        # Simple substitution for {subject_id}
        subj_value = self.params.get("subject_id", "")
        for name, value in list(script_parameters.items()):
            if not isinstance(value, str):
                continue
            original = value
            # Expand {subject_id}
            if "{subject_id}" in value:
                value = value.replace("{subject_id}", str(subj_value))
            # Expand any rig_param placeholders
            if "{rig_param:" in value:
                def repl(m):
                    key = m.group(1)
                    if key in self.params:
                        return str(self.params[key])
                    raise RuntimeError(f"rig_param placeholder references unknown key '{key}' for script parameter '{name}'")
                value = rig_pattern.sub(repl, value)
            if value != original:
                script_parameters[name] = value
        # No return needed; script_parameters mutated in place

    def _build_placeholder_context(self, params: Dict[str, Any]) -> Dict[str, str]:
        """Collect simple parameter values plus launcher metadata for string formatting."""
        context: Dict[str, str] = {}
        for key, value in params.items():
            if isinstance(value, (str, int, float)):
                context[key] = str(value)
        if self.subject_id:
            context.setdefault("subject_id", str(self.subject_id))
        if self.user_id:
            context.setdefault("user_id", str(self.user_id))
        if self.session_uuid:
            context.setdefault("session_uuid", str(self.session_uuid))
        if self.output_session_folder:
            context.setdefault("output_session_folder", str(self.output_session_folder))
            context.setdefault("session_folder", str(self.output_session_folder))
            context.setdefault("session_dir", str(self.output_session_folder))
        rig_id = self.rig_config.get("rig_id") if isinstance(self.rig_config, dict) else None
        if rig_id:
            context.setdefault("rig_id", str(rig_id))
        return context

    def _expand_parameter_placeholders(self, params: Dict[str, Any]) -> None:
        """Recursively substitute placeholder strings in parameter structures."""

        def _expand(value: Any, context: Dict[str, str]) -> Any:
            if isinstance(value, str):
                expanded = os.path.expandvars(value)
                try:
                    expanded = expanded.format_map(_PlaceholderDict(context))
                except Exception:
                    pass
                return expanded
            if isinstance(value, dict):
                return {k: _expand(v, context) for k, v in value.items()}
            if isinstance(value, list):
                return [_expand(item, context) for item in value]
            if isinstance(value, tuple):
                return tuple(_expand(item, context) for item in value)
            return value

        context = self._build_placeholder_context(params)
        for key in list(params.keys()):
            expanded = _expand(params[key], context)
            params[key] = expanded
            if isinstance(expanded, (str, int, float)):
                context[key] = str(expanded)
    
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
            
            output_handler = SharedFileHandler(output_log_path, encoding="utf-8")
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
                
                centralized_handler = SharedFileHandler(centralized_log_path, encoding="utf-8")
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
    
    def _run_stage(self, *, stage_name: str, pipeline_key: str, param_file: Optional[str] = None,
                   enable_legacy_repo_module: bool = False) -> bool:
        """Generic runner for pipeline stages (pre/post acquisition).

        Keeps BaseLauncher generic: modules can mutate params or write artifacts.
        Supports new unified schema and legacy repo_module entries.
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

        if self.session_uuid:
            params.setdefault("session_uuid", self.session_uuid)
        if self.output_session_folder:
            params.setdefault("output_session_folder", self.output_session_folder)
        self._expand_parameter_placeholders(params)

        pipeline = params.get(pipeline_key, [])
        repo_path = git_manager.get_repository_path(params)
        session_folder = params.get("output_session_folder") or self.output_session_folder
        all_success = True

        def _invoke_launcher_module(mod_name: str, merged_params: dict) -> bool:
            try:
                logging.info(f"{stage_name} launcher module: {mod_name}")
                pkg_stage = pipeline_key.replace('_pipeline', '')
                mod = importlib.import_module(f"openscope_experimental_launcher.{pkg_stage}.{mod_name}")
                # Preferred function name ordering
                candidates = [f"run_{pkg_stage}", "run"]
                func = None
                for cand in candidates:
                    if hasattr(mod, cand):
                        func = getattr(mod, cand)
                        break
                if not func:
                    logging.warning(f"Module {mod_name} has no callable entry point; skipping.")
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
                    target_name = os.path.basename(path_in_repo)
                    for root, _dirs, files in os.walk(repo_path):
                        if target_name in files:
                            abs_path = os.path.join(root, target_name)
                            break
                    if not os.path.isfile(abs_path):
                        raise FileNotFoundError(f"Script module file not found: {abs_path}")
                # Direct import using importlib.util (fallbacks removed)
                spec = importlib.util.spec_from_file_location(f"script_{pipeline_key}", abs_path)
                if not spec or not spec.loader:
                    raise ImportError(f"Could not create spec for script module: {abs_path}")
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[attr-defined]
                # New schema: function arguments are passed via a nested 'function_args' dict inside
                # module_parameters. Backward compatibility: if 'function_args' isn't provided we
                # fall back to legacy behavior (single params dict or positional heuristic).
                func_name = merged_params.get("function")
                func_args = merged_params.get("function_args")  # expected dict if present
                func = None
                preferred = [func_name, f"run_{pipeline_key.replace('_pipeline','')}", "run"]
                for cand in preferred:
                    if cand and hasattr(mod, cand):
                        func = getattr(mod, cand)
                        break
                if not func:
                    raise AttributeError("No callable entry point found in script module")
                import inspect
                sig = inspect.signature(func)
                # Invocation strategy simplified:
                # If function_args provided, ONLY pass those (plus derived output_path) as kwargs.
                # No automatic merging of other parameters. Caller must supply what it needs.
                # Otherwise fall back to legacy behaviors.
                # Expand placeholders and resolve relative paths inside function_args before calling.
                if func_args and isinstance(func_args, dict):
                    sess_dir = merged_params.get('output_session_folder') or merged_params.get('output_root_folder')
                    expanded_args = {}
                    for k, v in func_args.items():
                        if isinstance(v, str):
                            # Placeholder expansion
                            if '{session_folder}' in v and sess_dir:
                                v = v.replace('{session_folder}', sess_dir)
                            # Auto-resolve for *_path/_file keys if relative
                            if sess_dir and not os.path.isabs(v) and (k.endswith('_path') or k.endswith('_file')):
                                v = os.path.normpath(os.path.join(sess_dir, v))
                        expanded_args[k] = v
                    func_args = expanded_args
                if func_args and isinstance(func_args, dict):
                    call_kwargs = {}
                    for p_name in sig.parameters.keys():
                        if p_name in func_args:
                            call_kwargs[p_name] = func_args[p_name]
                        elif p_name == 'output_path' and 'output_filename' in func_args:
                            sess_dir = merged_params.get('output_session_folder') or merged_params.get('output_root_folder')
                            call_kwargs[p_name] = os.path.join(sess_dir, func_args['output_filename'])
                    result = func(**call_kwargs)
                elif len(sig.parameters) == 0:
                    result = func()
                elif len(sig.parameters) == 1:
                    result = func(merged_params)
                else:
                    ordered = []
                    for p_name, p in sig.parameters.items():
                        if p_name in merged_params:
                            ordered.append(merged_params[p_name])
                        elif p_name == 'output_path' and 'output_filename' in merged_params:
                            sess_dir = merged_params.get('output_session_folder') or merged_params.get('output_root_folder')
                            ordered.append(os.path.join(sess_dir, merged_params['output_filename']))
                        else:
                            ordered.append(None if p.default is inspect._empty else p.default)
                    result = func(*ordered)
                return result in (None, 0, True)
            except Exception as e:
                logging.error(f"Script module error {path_in_repo}: {e}")
                return False

        for raw_entry in pipeline:
            if enable_legacy_repo_module and isinstance(raw_entry, dict) and raw_entry.get('type') == 'repo_module':
                legacy_path = raw_entry.get('repo_relative_path')
                legacy_func = raw_entry.get('function')
                legacy_kwargs = raw_entry.get('kwargs', {}) or {}
                merged = dict(params)
                merged.update(legacy_kwargs)
                if session_folder:
                    merged.setdefault('output_session_folder', session_folder)
                if legacy_func:
                    merged.setdefault('function', legacy_func)
                ok = _invoke_script_module(legacy_path, merged)
                if not ok:
                    all_success = False
                    logging.error(f"{stage_name} legacy repo_module failed: {legacy_path}")
                else:
                    logging.info(f"{stage_name} legacy repo_module completed: {legacy_path}")
                continue

            if isinstance(raw_entry, str):
                entry = {"module_type": "launcher_module", "module_path": raw_entry, "module_parameters": {}}
            elif isinstance(raw_entry, dict):
                entry = raw_entry
            else:
                logging.warning(f"Ignoring unsupported pipeline entry: {raw_entry}")
                continue
            module_type = entry.get('module_type', 'launcher_module')
            module_path = entry.get('module_path')
            module_params = entry.get('module_parameters', {}) or {}
            merged = dict(params)
            merged.update(module_params)
            if session_folder:
                merged.setdefault('output_session_folder', session_folder)
            if module_type == 'launcher_module':
                ok = _invoke_launcher_module(module_path, merged)
            elif module_type == 'script_module':
                ok = _invoke_script_module(module_path, merged)
            else:
                logging.warning(f"Unknown module_type '{module_type}' in {stage_name} entry")
                continue
            if not ok:
                all_success = False
                logging.error(f"{stage_name} step failed: {module_path}")
            else:
                logging.info(f"{stage_name} step completed: {module_path}")

        if all_success:
            logging.info(f"All {stage_name.lower()} steps completed successfully.")
        else:
            logging.warning(f"Some {stage_name.lower()} steps failed. See logs.")
        self.params.update(params)
        return all_success

    # Public wrappers expected by tests
    def run_pre_acquisition(self, param_file: Optional[str] = None, enable_legacy_repo_module: bool = True) -> bool:
        return self._run_stage(
            stage_name="Pre-acquisition",
            pipeline_key="pre_acquisition_pipeline",
            param_file=param_file,
            enable_legacy_repo_module=enable_legacy_repo_module,
        )

    def run_post_acquisition(self, param_file: Optional[str] = None, enable_legacy_repo_module: bool = True) -> bool:
        return self._run_stage(
            stage_name="Post-acquisition",
            pipeline_key="post_acquisition_pipeline",
            param_file=param_file,
            enable_legacy_repo_module=enable_legacy_repo_module,
        )
    
    def cleanup(self):
        """Clean up resources when the script exits."""
        logging.info("Cleaning up resources...")
        try:
            self.stop()
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
        return None
    
    def _start_resource_logging(self, session_folder: str, acquisition_pid: Optional[int] = None):
        """Start resource logging thread once; supports later PID injection without data loss.

        If called multiple times, subsequent calls are ignored. Acquisition PID can be set
        later via `set_resource_logging_pid`.
        """
        if hasattr(self, '_resource_log_thread') and getattr(self, '_resource_log_thread'):
            return  # Already running; do not restart
        launcher_metadata_dir = os.path.join(session_folder, "launcher_metadata")
        os.makedirs(launcher_metadata_dir, exist_ok=True)
        self._resource_log_file = os.path.join(launcher_metadata_dir, "resource_usage.json")
        self._resource_log_stop = threading.Event()
        if not hasattr(self, '_resource_log_data'):
            self._resource_log_data = []
        self._resource_log_interval = self.params.get("resource_log_interval", 5)
        self._resource_logging_acq_pid = acquisition_pid
        def log_loop():
            import psutil, datetime, json, time
            launcher_proc = psutil.Process(os.getpid())
            acq_proc = None
            while not self._resource_log_stop.is_set():
                # Attempt to resolve acquisition process if we have a PID and not yet a handle
                if self._resource_logging_acq_pid and acq_proc is None:
                    try:
                        acq_proc = psutil.Process(self._resource_logging_acq_pid)
                    except Exception:
                        acq_proc = None
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
                try:
                    with open(self._resource_log_file, "w") as f:
                        json.dump(self._resource_log_data, f, indent=2)
                except Exception:
                    pass
                time.sleep(self._resource_log_interval)
        self._resource_log_thread = threading.Thread(target=log_loop, daemon=True)
        self._resource_log_thread.start()

    def set_resource_logging_pid(self, acquisition_pid: int):
        """Inject acquisition PID for resource logging without restarting thread."""
        self._resource_logging_acq_pid = acquisition_pid

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
            if self.session_uuid:
                self.params["session_uuid"] = self.session_uuid

            # Resolve placeholders now that session metadata is available
            self._expand_parameter_placeholders(self.params)

            # Set up logging and metadata
            if output_session_folder:
                centralized_log_dir = self.params.get("centralized_log_directory")
                self.setup_continuous_logging(output_session_folder, centralized_log_dir)
                self.save_launcher_metadata(output_session_folder)
                # Start resource logging (launcher only for now) always enabled
                self._start_resource_logging(output_session_folder, acquisition_pid=None)

            # Run pre-acquisition steps
            if not self.run_pre_acquisition():
                logging.warning("Pre-acquisition processing failed, but continuing with experiment.")

            # Start the experiment (implemented by interface-specific launchers)
            experiment_success = self.start_experiment()

            # Update resource logger to include acquisition PID
            if self.process is not None:
                try:
                    self.set_resource_logging_pid(self.process.pid)
                except Exception as e:
                    logging.warning(f"Could not inject acquisition PID for resource logging: {e}")

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
        """Check if the experiment completed successfully based on process return code."""
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
            if not self.process or not getattr(self.process, 'stdout', None):
                return
            if hasattr(self.process.stdout, '_mock_name'):
                return
            try:
                for line in iter(self.process.stdout.readline, b''):
                    if not line:
                        break
                    line_str = line.decode('utf-8').rstrip() if isinstance(line, bytes) else line.rstrip()
                    if line_str:
                        self.stdout_data.append(line_str)
                        logging.info(f"{self._get_launcher_type_name()} output: {line_str}")
            except Exception as e:
                logging.debug(f"stdout reader error: {e}")
            finally:
                try:
                    self.process.stdout.close()
                except Exception:
                    pass

        def stderr_reader():
            if not self.process or not getattr(self.process, 'stderr', None):
                return
            if hasattr(self.process.stderr, '_mock_name'):
                return
            try:
                for line in iter(self.process.stderr.readline, b''):
                    if not line:
                        break
                    line_str = line.decode('utf-8').rstrip() if isinstance(line, bytes) else line.rstrip()
                    if line_str:
                        self.stderr_data.append(line_str)
                        logging.error(f"{self._get_launcher_type_name()} error: {line_str}")
                        if not hasattr(self, '_first_stderr_ts'):
                            self._first_stderr_ts = time.time()
            except Exception as e:
                logging.debug(f"stderr reader error: {e}")
            finally:
                try:
                    self.process.stderr.close()
                except Exception:
                    pass

        self._output_threads = [
            threading.Thread(target=stdout_reader, daemon=True),
            threading.Thread(target=stderr_reader, daemon=True)
        ]
        for t in self._output_threads:
            t.start()

    # === Added generic lifecycle helpers (previously removed during refactor) ===
    def signal_handler(self, sig, frame):  # type: ignore[override]
        """Handle SIGINT (Ctrl+C) to stop experiment cleanly."""
        logging.info("Interrupt received; stopping experiment...")
        try:
            self.stop()
        except Exception as e:
            logging.error(f"Error during interrupt stop: {e}")
        raise SystemExit(0)

    def stop(self):
        """Stop acquisition process (if running) and finalize logging."""
        if hasattr(self, 'stop_time') and self.stop_time is None:
            self.stop_time = datetime.datetime.now()
        proc = getattr(self, 'process', None)
        if proc is not None and getattr(proc, 'poll', lambda: None)() is None:
            try:
                logging.info("Terminating acquisition process...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logging.warning("Process did not exit after terminate; killing")
                    proc.kill()
            except Exception as e:
                logging.error(f"Error terminating process: {e}")
        # Tests expect None return
        return None

    def get_process_errors(self):
        """Return accumulated stderr lines as a list."""
        return list(getattr(self, 'stderr_data', []))

    def _get_launcher_type_name(self) -> str:
        """Return a human-readable launcher type name."""
        return self.__class__.__name__

    def _monitor_process(self):
        """Monitor process; support optional fail-fast termination on stderr errors."""
        proc = getattr(self, 'process', None)
        if proc is None:
            logging.warning("No process to monitor.")
            return
        fail_fast = self.params.get('acquisition_error_terminate') is True
        grace = 0.0
        if fail_fast:
            try:
                grace = float(self.params.get('acquisition_error_grace_period_sec', 0))
            except Exception:
                grace = 0.0
        start_timeout = float(self.params.get('process_start_timeout_sec', 0) or 0)
        start_deadline = time.time() + start_timeout if start_timeout > 0 else None
        try:
            if not fail_fast and not start_deadline:
                proc.wait()
                return
            # Polling loop with 0.5s interval
            while True:
                rc = proc.poll()
                if rc is not None:
                    break
                if start_deadline and time.time() > start_deadline and not (self.stdout_data or self.stderr_data):
                    logging.error("Process start timeout exceeded; terminating.")
                    try:
                        proc.terminate(); proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        logging.warning("Process did not exit after timeout terminate; killing.")
                        try: proc.kill()
                        except Exception: pass
                    break
                if fail_fast and hasattr(self, '_first_stderr_ts'):
                    elapsed = time.time() - getattr(self, '_first_stderr_ts', 0)
                    if elapsed >= grace:
                        logging.error(f"Fail-fast termination after stderr error (grace {grace}s).")
                        try:
                            proc.terminate()
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            logging.warning("Process did not exit; killing.")
                            try:
                                proc.kill()
                            except Exception:
                                pass
                        break
                time.sleep(0.5)
        except Exception as e:
            logging.error(f"Monitoring error: {e}")

    def save_end_state(self, output_directory: Optional[str]):
        """Persist final launcher state for downstream post-acquisition tools."""
        if not output_directory:
            return None
        try:
            md_dir = os.path.join(output_directory, "launcher_metadata")
            os.makedirs(md_dir, exist_ok=True)
            end_state_path = os.path.join(md_dir, "end_state.json")
            # Flattened schema: put core fields at top-level (remove legacy session_info nesting)
            start_time_iso = self.start_time.isoformat() if self.start_time else None
            stop_time_iso = self.stop_time.isoformat() if self.stop_time else None
            # Provide rig_config and experiment_data (if available)
            rig_config = getattr(self, 'rig_config', {}) or {}
            experiment_notes = getattr(self, 'experiment_notes', None)
            experiment_data = {}
            if experiment_notes:
                experiment_data['experiment_notes'] = experiment_notes
            data = {
                "session_uuid": self.session_uuid,
                "subject_id": self.subject_id,
                "user_id": self.user_id,
                "start_time": start_time_iso,
                "stop_time": stop_time_iso,
                "process_returncode": getattr(self.process, 'returncode', None),
                "version": self._version,
                "rig_config": rig_config,
                "experiment_data": experiment_data,
            }
            with open(end_state_path, 'w') as f:
                json.dump(data, f, indent=2)
            logging.info(f"Saved end_state to {end_state_path}")
            return True
        except Exception as e:
            logging.error(f"Failed to save end_state: {e}")
            return None

    def save_debug_state(self, output_directory: Optional[str], exc: Exception):
        """Persist debug information when an unexpected exception occurs."""
        if not output_directory:
            return None
        try:
            md_dir = os.path.join(output_directory, "launcher_metadata")
            os.makedirs(md_dir, exist_ok=True)
            debug_path = os.path.join(md_dir, "debug_state.json")
            # Snapshot of launcher __dict__ (shallow) for state inspection; ensure JSON-serializable
            def _serialize(val):
                if isinstance(val, (datetime.datetime, datetime.date)):
                    return val.isoformat()
                if isinstance(val, (list, tuple)):
                    return [ _serialize(x) for x in val ]
                if isinstance(val, dict):
                    return {k: _serialize(v) for k, v in val.items()}
                try:
                    json.dumps(val)
                    return val
                except Exception:
                    return repr(val)
            launcher_state = {k: _serialize(v) for k, v in self.__dict__.items() if not k.startswith('_')}
            info = {
                "exception": repr(exc),
                "traceback": traceback.format_exc(),
                "timestamp": datetime.datetime.now().isoformat(),
                "session_uuid": self.session_uuid,
                "crash_info": {
                    "exception_type": exc.__class__.__name__,
                    "message": str(exc),
                    "crash_time": datetime.datetime.now().isoformat()  # added for test expectations
                },
                "launcher_state": launcher_state,
            }
            with open(debug_path, 'w') as f:
                json.dump(info, f, indent=2)
            logging.info(f"Saved debug_state to {debug_path}")
            return True
        except Exception as e:
            logging.error(f"Failed to save debug_state: {e}")
            return None


def run_from_params(param_file):
    """
    Module-level entry point for the unified launcher wrapper.
    Calls BaseLauncher.run_from_params.
    """
    return BaseLauncher.run_from_params(param_file)
