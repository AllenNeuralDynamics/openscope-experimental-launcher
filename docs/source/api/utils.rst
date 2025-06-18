API Reference - Utils Module
============================

The utils module provides utility classes and functions that support the core functionality of the OpenScope Experimental Launcher.

Overview
--------

The utils module contains helper classes for:

- **ConfigLoader**: Loading and parsing CamStim-style configuration files
- **GitManager**: Git repository operations and version control
- **ProcessMonitor**: Process health monitoring and resource tracking
- **FileUtils**: File system operations and path management
- **ValidationUtils**: Parameter validation and schema checking

ConfigLoader Class
------------------

.. autoclass:: openscope_experimental_launcher.utils.config_loader.ConfigLoader
   :members:
   :undoc-members:
   :show-inheritance:

   Handles loading and parsing of CamStim-style configuration files.

   **Features:**
   - Parse .cfg files with section-based configuration
   - Environment variable substitution
   - Type conversion and validation
   - Default value handling

GitManager Class
----------------

.. autoclass:: openscope_experimental_launcher.utils.git_manager.GitManager
   :members:
   :undoc-members:
   :show-inheritance:

   Manages Git repository operations including cloning, checkout, and version tracking.

   **Features:**
   - Repository cloning with progress tracking
   - Branch and commit checkout
   - Version tracking and metadata
   - Repository validation

ProcessMonitor Class
--------------------

.. autoclass:: openscope_experimental_launcher.utils.process_monitor.ProcessMonitor
   :members:
   :undoc-members:
   :show-inheritance:

   Monitors process health, memory usage, and handles cleanup operations.

   **Features:**
   - Real-time memory usage monitoring
   - Process termination handling
   - Windows job object management
   - Resource cleanup

Example Usage
-------------

Configuration Loading
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.utils.config_loader import ConfigLoader

   # Load CamStim configuration file
   config_loader = ConfigLoader()
   config = config_loader.load("C:/ProgramData/AIBS_MPE/camstim/config/stim.cfg")

   # Access configuration values
   display_config = config.get('display', {})
   print(f"Monitor refresh rate: {display_config.get('refresh_rate', 60)}")

   # Load with environment variable substitution
   config_with_env = config_loader.load_with_env_substitution("config.cfg")

Git Repository Management
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.utils.git_manager import GitManager

   # Initialize Git manager
   git_manager = GitManager()

   # Clone repository
   repo_path = git_manager.clone_repository(
       url="https://github.com/AllenNeuralDynamics/openscope-community-predictive-processing.git",
       local_path="C:/BonsaiWorkflows/PredictiveProcessing",
       commit_hash="main"
   )

   # Get repository information
   repo_info = git_manager.get_repository_info(repo_path)
   print(f"Current commit: {repo_info['commit_hash']}")
   print(f"Branch: {repo_info['branch']}")
   print(f"Last modified: {repo_info['last_modified']}")

Process Monitoring
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.utils.process_monitor import ProcessMonitor
   import subprocess

   # Start a process
   process = subprocess.Popen(["python", "long_running_script.py"])

   # Monitor the process
   monitor = ProcessMonitor(process)
   
   # Check memory usage periodically
   while process.poll() is None:
       memory_info = monitor.get_memory_usage()
       print(f"Memory usage: {memory_info['percent']}%")
       
       # Terminate if memory usage is too high
       if memory_info['percent'] > 80:
           monitor.terminate_process()
           break
       
       time.sleep(1)

Utility Functions
-----------------

File System Utilities
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.utils.file_utils import (
       ensure_directory_exists,
       get_file_checksum,
       safe_file_copy,
       cleanup_temp_files
   )

   # Ensure output directory exists
   output_dir = "C:/ExperimentData/2025-06-13"
   ensure_directory_exists(output_dir)

   # Calculate file checksum for integrity checking
   checksum = get_file_checksum("experiment_params.json")
   print(f"Parameter file checksum: {checksum}")

   # Safe file copying with error handling
   success = safe_file_copy(
       source="temp_results.pkl",
       destination="final_results.pkl",
       create_backup=True
   )

Validation Utilities
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.utils.validation_utils import (
       validate_parameter_schema,
       validate_file_paths,
       validate_git_url,
       sanitize_filename
   )

   # Validate parameter structure
   params = {
       "subject_id": "test_mouse",
       "user_id": "researcher",
       "repository_url": "https://github.com/user/repo.git"
   }

   validation_result = validate_parameter_schema(params)
   if not validation_result.is_valid:
       print(f"Validation errors: {validation_result.errors}")

   # Validate file paths exist
   paths_to_check = [
       "C:/Bonsai/Bonsai.exe",
       "workflow.bonsai",
       "output_directory"
   ]
   
   path_validation = validate_file_paths(paths_to_check)
   missing_paths = [path for path, exists in path_validation.items() if not exists]
   
   if missing_paths:
       print(f"Missing files/directories: {missing_paths}")

Advanced Usage
--------------

Custom Configuration Parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.utils.config_loader import ConfigLoader

   class CustomConfigLoader(ConfigLoader):
       """Extended config loader with custom parsing logic."""
       
       def load_experimental_config(self, config_path):
           """Load config with experimental parameter validation."""
           config = self.load(config_path)
           
           # Apply custom validation
           self._validate_experimental_parameters(config)
           
           # Add computed values
           config['computed'] = self._compute_derived_values(config)
           
           return config
       
       def _validate_experimental_parameters(self, config):
           """Validate experiment-specific configuration."""
           required_sections = ['stimulus', 'recording', 'output']
           
           for section in required_sections:
               if section not in config:
                   raise ValueError(f"Missing required config section: {section}")
       
       def _compute_derived_values(self, config):
           """Compute derived configuration values."""
           stimulus_config = config.get('stimulus', {})
           recording_config = config.get('recording', {})
           
           return {
               'estimated_duration_seconds': stimulus_config.get('trial_count', 100) * 
                                           stimulus_config.get('trial_duration', 5),
               'estimated_file_size_mb': recording_config.get('sampling_rate', 1000) * 
                                       recording_config.get('channel_count', 64) * 0.001
           }

Repository Caching System
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.utils.git_manager import GitManager
   import os
   import json

   class CachedGitManager(GitManager):
       """Git manager with local repository caching."""
       
       def __init__(self, cache_dir="C:/BonsaiCache"):
           super().__init__()
           self.cache_dir = cache_dir
           self.cache_index_file = os.path.join(cache_dir, "cache_index.json")
           self._load_cache_index()
       
       def clone_or_update_repository(self, url, commit_hash="main"):
           """Clone repository or update existing cached copy."""
           cache_key = self._get_cache_key(url, commit_hash)
           cached_path = self._get_cached_path(cache_key)
           
           if self._is_cache_valid(cached_path, commit_hash):
               print(f"Using cached repository: {cached_path}")
               return cached_path
           
           # Clone to cache
           repo_path = self.clone_repository(url, cached_path, commit_hash)
           self._update_cache_index(cache_key, url, commit_hash, repo_path)
           
           return repo_path
       
       def _get_cache_key(self, url, commit_hash):
           """Generate cache key for repository."""
           import hashlib
           key_string = f"{url}#{commit_hash}"
           return hashlib.md5(key_string.encode()).hexdigest()
       
       def _is_cache_valid(self, cached_path, expected_commit):
           """Check if cached repository is valid and up-to-date."""
           if not os.path.exists(cached_path):
               return False
           
           try:
               current_commit = self.get_repository_info(cached_path)['commit_hash']
               return current_commit.startswith(expected_commit[:8])  # Short hash match
           except:
               return False

Process Resource Manager
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from openscope_experimental_launcher.utils.process_monitor import ProcessMonitor
   import psutil
   import threading
   import time

   class ResourceManager:
       """Advanced process resource management."""
       
       def __init__(self, memory_limit_percent=80, cpu_limit_percent=90):
           self.memory_limit = memory_limit_percent
           self.cpu_limit = cpu_limit_percent
           self.monitors = {}
           self.monitoring_active = False
           self.monitor_thread = None
       
       def add_process(self, process, name):
           """Add process to resource monitoring."""
           monitor = ProcessMonitor(process)
           self.monitors[name] = {
               'monitor': monitor,
               'process': process,
               'start_time': time.time(),
               'peak_memory': 0,
               'peak_cpu': 0
           }
       
       def start_monitoring(self, interval=1.0):
           """Start resource monitoring thread."""
           self.monitoring_active = True
           self.monitor_thread = threading.Thread(
               target=self._monitor_loop,
               args=(interval,),
               daemon=True
           )
           self.monitor_thread.start()
       
       def stop_monitoring(self):
           """Stop resource monitoring."""
           self.monitoring_active = False
           if self.monitor_thread:
               self.monitor_thread.join(timeout=5.0)
       
       def get_resource_summary(self):
           """Get summary of resource usage for all monitored processes."""
           summary = {}
           
           for name, info in self.monitors.items():
               if info['process'].poll() is None:  # Process still running
                   current_memory = info['monitor'].get_memory_usage()
                   summary[name] = {
                       'status': 'running',
                       'duration_seconds': time.time() - info['start_time'],
                       'current_memory_percent': current_memory['percent'],
                       'peak_memory_percent': info['peak_memory'],
                       'peak_cpu_percent': info['peak_cpu']
                   }
               else:
                   summary[name] = {
                       'status': 'completed',
                       'duration_seconds': time.time() - info['start_time'],
                       'exit_code': info['process'].returncode
                   }
           
           return summary
       
       def _monitor_loop(self, interval):
           """Main monitoring loop."""
           while self.monitoring_active:
               for name, info in self.monitors.items():
                   if info['process'].poll() is None:  # Still running
                       try:
                           # Check memory usage
                           memory_info = info['monitor'].get_memory_usage()
                           info['peak_memory'] = max(info['peak_memory'], 
                                                   memory_info['percent'])
                           
                           # Check CPU usage
                           cpu_percent = psutil.Process(info['process'].pid).cpu_percent()
                           info['peak_cpu'] = max(info['peak_cpu'], cpu_percent)
                           
                           # Check limits
                           if memory_info['percent'] > self.memory_limit:
                               print(f"Process {name} exceeded memory limit, terminating")
                               info['monitor'].terminate_process()
                           
                           if cpu_percent > self.cpu_limit:
                               print(f"Process {name} exceeded CPU limit, terminating")
                               info['monitor'].terminate_process()
                               
                       except (psutil.NoSuchProcess, psutil.AccessDenied):
                           # Process may have terminated
                           pass
               
               time.sleep(interval)

Error Handling and Logging
---------------------------

Utility Error Classes
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Custom exception classes for utility modules
   class ConfigLoaderError(Exception):
       """Raised when configuration loading fails."""
       pass

   class GitManagerError(Exception):
       """Raised when Git operations fail."""
       pass

   class ProcessMonitorError(Exception):
       """Raised when process monitoring fails."""
       pass

   # Usage example with proper error handling
   from openscope_experimental_launcher.utils.config_loader import ConfigLoader, ConfigLoaderError

   try:
       config_loader = ConfigLoader()
       config = config_loader.load("nonexistent_config.cfg")
   except ConfigLoaderError as e:
       print(f"Configuration loading failed: {e}")
       # Use default configuration
       config = load_default_config()
   except Exception as e:
       print(f"Unexpected error: {e}")

Logging Configuration
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import logging
   from openscope_experimental_launcher.utils.git_manager import GitManager

   # Configure logging for utility modules
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )

   # Use utilities with logging
   git_manager = GitManager()
   
   # Git operations will log progress and errors
   try:
       repo_path = git_manager.clone_repository(
           "https://github.com/user/repo.git",
           "local_path"
       )
   except Exception as e:
       logging.error(f"Repository cloning failed: {e}")

Testing Utilities
-----------------

Mock Utilities for Testing
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from unittest.mock import Mock, patch
   from openscope_experimental_launcher.utils.git_manager import GitManager

   def test_git_manager_with_mock():
       """Test GitManager with mocked Git operations."""
       
       with patch('subprocess.run') as mock_run:
           # Mock successful git clone
           mock_run.return_value.returncode = 0
           
           git_manager = GitManager()
           result = git_manager.clone_repository(
               "https://github.com/test/repo.git",
               "test_path"
           )
           
           # Verify git command was called
           mock_run.assert_called()
           assert result == "test_path"

   def test_process_monitor_with_mock():
       """Test ProcessMonitor with mocked process."""
       
       mock_process = Mock()
       mock_process.pid = 12345
       mock_process.poll.return_value = None  # Still running
       
       from openscope_experimental_launcher.utils.process_monitor import ProcessMonitor
       
       monitor = ProcessMonitor(mock_process)
       
       # Mock memory usage
       with patch('psutil.Process') as mock_psutil:
           mock_psutil.return_value.memory_info.return_value.rss = 100 * 1024 * 1024  # 100MB
           mock_psutil.return_value.memory_percent.return_value = 25.0
           
           memory_info = monitor.get_memory_usage()
           assert memory_info['percent'] == 25.0