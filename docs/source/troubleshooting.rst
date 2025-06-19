Troubleshooting Guide
====================

This guide helps you diagnose and resolve common issues when using the OpenScope Experimental Launcher.

Common Issues and Solutions
---------------------------

Experiment Launch Failures
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem: Experiment fails to start**

.. code-block:: text

   ERROR: Failed to start experiment: Repository clone failed

**Possible Causes:**
- Network connectivity issues
- Invalid Git repository URL
- Authentication problems
- Insufficient disk space

**Solutions:**

1. **Check network connectivity:**

   .. code-block:: bash

      ping github.com
      # Test Git access
      git ls-remote https://github.com/AllenNeuralDynamics/openscope-community-predictive-processing.git

2. **Verify repository URL:**

   .. code-block:: python

      from openscope_experimental_launcher.utils.validation_utils import validate_git_url
      
      url = "https://github.com/user/repo.git"
      is_valid = validate_git_url(url)
      print(f"URL valid: {is_valid}")

3. **Check disk space:**

   .. code-block:: python

      import shutil
      
      free_space = shutil.disk_usage("C:/").free / (1024**3)
      print(f"Free space: {free_space:.1f} GB")

4. **Test with minimal parameters:**

   .. code-block:: python

      # Minimal test parameters
      params = {
          "subject_id": "test_mouse",
          "user_id": "test_user",
          "repository_url": "https://github.com/AllenNeuralDynamics/openscope-community-predictive-processing.git",
          "output_directory": "C:/TestOutput"
      }

Bonsai Process Issues
~~~~~~~~~~~~~~~~~~~~~

**Problem: Bonsai workflow crashes or hangs**

.. code-block:: text

   ERROR: Bonsai process terminated unexpectedly (exit code: -1)

**Diagnostic Steps:**

1. **Check Bonsai installation:**

   .. code-block:: python

      from pathlib import Path
      
      bonsai_paths = [
          "C:/Program Files/Bonsai/Bonsai.exe",
          "C:/Bonsai/Bonsai.exe",
          "bonsai/Bonsai.exe"  # Local installation
      ]
      
      for path in bonsai_paths:
          if Path(path).exists():
              print(f"Found Bonsai at: {path}")

2. **Test Bonsai workflow manually:**

   .. code-block:: bash

      # Run Bonsai workflow directly
      "C:/Program Files/Bonsai/Bonsai.exe" --start workflow.bonsai

3. **Check workflow file integrity:**

   .. code-block:: python

      from openscope_experimental_launcher.utils.file_utils import get_file_checksum
      
      workflow_path = "path/to/workflow.bonsai"
      checksum = get_file_checksum(workflow_path)
      print(f"Workflow checksum: {checksum}")

4. **Monitor process resources:**

   .. code-block:: python

      from openscope_experimental_launcher.utils.process_monitor import ProcessMonitor
      import subprocess
      
      # Start Bonsai with monitoring
      process = subprocess.Popen(["Bonsai.exe", "workflow.bonsai"])
      monitor = ProcessMonitor(process)
      
      # Check memory usage
      memory_info = monitor.get_memory_usage()
      print(f"Memory usage: {memory_info}")

Configuration File Problems
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem: Configuration file parsing errors**

.. code-block:: text

   ERROR: Failed to parse configuration file: Invalid syntax at line 15

**Solutions:**

1. **Validate configuration syntax:**

   .. code-block:: python

      from openscope_experimental_launcher.utils.config_loader import ConfigLoader
      
      try:
          loader = ConfigLoader()
          config = loader.load("config.cfg")
          print("Configuration valid")
      except Exception as e:
          print(f"Configuration error: {e}")

2. **Use configuration validation tool:**

   .. code-block:: python

      from openscope_experimental_launcher.utils.validation_utils import validate_config_file
      
      validation_result = validate_config_file("config.cfg")
      if not validation_result.is_valid:
          for error in validation_result.errors:
              print(f"Line {error.line}: {error.message}")

3. **Create minimal valid configuration:**

   .. code-block:: ini

      [display]
      refresh_rate = 60
      resolution = 1920x1080
      
      [stimulus]
      duration = 5.0
      repetitions = 10

Output File Issues
~~~~~~~~~~~~~~~~~~

**Problem: Missing or corrupted output files**

.. code-block:: text

   WARNING: Expected output file not found: session_data.pkl

**Diagnostic Steps:**

1. **Check output directory permissions:**

   .. code-block:: python

      import os
      from pathlib import Path
      
      output_dir = Path("C:/ExperimentData")
      
      # Check if directory exists and is writable
      if output_dir.exists():
          test_file = output_dir / "write_test.txt"
          try:
              test_file.write_text("test")
              test_file.unlink()
              print("Output directory writable")
          except Exception as e:
              print(f"Output directory not writable: {e}")
      else:
          print("Output directory does not exist")

2. **Verify file creation during experiment:**   .. code-block:: python

      from openscope_experimental_launcher.launchers import BaseLauncher
      import time
      
      class DiagnosticLauncher(BaseLauncher):
          def run(self, param_file):
              # Override run method to add file monitoring
              result = super().run(param_file)
              
              # Check what files were actually created
              if hasattr(self, 'session_directory') and self.session_directory:
                  output_path = Path(self.session_directory)
                  if output_path.exists():
                      print(f"Output directory created: {output_path}")
                      print(f"Number of files: {len(list(output_path.glob('*')))}")
                  else:
                      print("Output file was not created")
              
              return result

3. **Recover partial data:**

   .. code-block:: python

      def recover_experiment_data(experiment_uuid):
          """Attempt to recover data from failed experiment."""
          
          possible_locations = [
              f"C:/ExperimentData/{experiment_uuid}",
              f"C:/temp/{experiment_uuid}",
              f"./output/{experiment_uuid}"
          ]
          
          recovered_files = []
          
          for location in possible_locations:
              path = Path(location)
              if path.exists():
                  files = list(path.glob("*"))
                  recovered_files.extend(files)
          
          return recovered_files

Memory and Performance Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem: Experiment consumes excessive memory or CPU**

.. code-block:: text

   WARNING: Process memory usage exceeds 80% (2.1GB used)

**Solutions:**

1. **Monitor resource usage:**

   .. code-block:: python

      from openscope_experimental_launcher.utils.process_monitor import ProcessMonitor
      import psutil
      import threading
      import time
      
      def monitor_resources(process, duration=60):
          """Monitor process resources for specified duration."""
          
          monitor = ProcessMonitor(process)
          start_time = time.time()
          
          while time.time() - start_time < duration:
              if process.poll() is not None:
                  break
              
              memory_info = monitor.get_memory_usage()
              cpu_percent = psutil.Process(process.pid).cpu_percent(interval=1)
              
              print(f"Memory: {memory_info['percent']:.1f}%, CPU: {cpu_percent:.1f}%")
              
              # Alert if usage is high
              if memory_info['percent'] > 80:
                  print("⚠️  High memory usage detected")
              if cpu_percent > 90:
                  print("⚠️  High CPU usage detected")
              
              time.sleep(5)

2. **Implement resource limits:**   .. code-block:: python

      class ResourceLimitedLauncher(BaseLauncher):
          def __init__(self, memory_limit_mb=2048, cpu_limit_percent=80):
              super().__init__()
              self.memory_limit = memory_limit_mb
              self.cpu_limit = cpu_limit_percent
          
          def run(self, param_file):
              # Start monitoring in background thread
              monitor_thread = threading.Thread(
                  target=self._monitor_resources,
                  daemon=True
              )
              monitor_thread.start()
              
              return super().run(param_file)
          
          def _monitor_resources(self):
              """Background resource monitoring."""
              while self.bonsai_process and self.bonsai_process.poll() is None:
                  try:
                      process = psutil.Process(self.bonsai_process.pid)
                      
                      # Check memory
                      memory_mb = process.memory_info().rss / (1024 * 1024)
                      if memory_mb > self.memory_limit:
                          print(f"Memory limit exceeded: {memory_mb:.1f}MB")
                          self.stop()
                          break
                      
                      # Check CPU
                      cpu_percent = process.cpu_percent(interval=1)
                      if cpu_percent > self.cpu_limit:
                          print(f"CPU limit exceeded: {cpu_percent:.1f}%")
                          self.stop()
                          break
                  
                  except (psutil.NoSuchProcess, psutil.AccessDenied):
                      break
                  
                  time.sleep(5)

3. **Optimize workflow parameters:**

   .. code-block:: python

      def optimize_workflow_parameters(base_params):
          """Suggest optimized parameters for better performance."""
          
          optimized = base_params.copy()
          
          # Reduce trial count for testing
          if 'num_trials' in optimized and optimized['num_trials'] > 100:
              optimized['num_trials'] = min(optimized['num_trials'], 100)
              print("⚡ Reduced trial count for testing")
          
          # Optimize frame rates
          if 'slap_fovs' in optimized:
              for fov in optimized['slap_fovs']:
                  if 'frame_rate' in fov and fov['frame_rate'] > 30:
                      fov['frame_rate'] = 30
                      print("⚡ Reduced frame rate for performance")
          
          return optimized

Network and Connectivity Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem: Repository cloning fails due to network issues**

.. code-block:: text

   ERROR: fatal: unable to access 'https://github.com/...': SSL certificate problem

**Solutions:**

1. **Test network connectivity:**

   .. code-block:: python

      import requests
      import socket
      
      def test_connectivity():
          """Test network connectivity to common services."""
          
          tests = [
              ("GitHub API", "https://api.github.com"),
              ("GitHub Raw", "https://raw.githubusercontent.com"),
              ("Google DNS", "8.8.8.8")
          ]
          
          for name, target in tests:
              try:
                  if target.startswith("http"):
                      response = requests.get(target, timeout=10)
                      status = f"HTTP {response.status_code}"
                  else:
                      socket.create_connection((target, 53), timeout=10)
                      status = "Connected"
                  
                  print(f"✅ {name}: {status}")
              
              except Exception as e:
                  print(f"❌ {name}: {e}")

2. **Configure Git for corporate networks:**

   .. code-block:: bash

      # Disable SSL verification (temporary fix)
      git config --global http.sslVerify false
      
      # Configure proxy if needed
      git config --global http.proxy http://proxy.company.com:8080

3. **Use alternative repository access:**

   .. code-block:: python

      def try_repository_access(repo_url):
          """Try different methods to access repository."""
          
          methods = [
              ("HTTPS", repo_url),
              ("HTTP", repo_url.replace("https://", "http://")),
              ("Git Protocol", repo_url.replace("https://", "git://"))
          ]
          
          for method, url in methods:
              try:
                  # Test with git ls-remote
                  result = subprocess.run(
                      ["git", "ls-remote", url],
                      capture_output=True,
                      timeout=30
                  )
                  
                  if result.returncode == 0:
                      print(f"✅ {method} works: {url}")
                      return url
                  else:
                      print(f"❌ {method} failed: {result.stderr.decode()}")
              
              except Exception as e:
                  print(f"❌ {method} error: {e}")
          
          return None

Advanced Diagnostics
--------------------

Comprehensive System Check
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def run_system_diagnostics():
       """Run comprehensive system diagnostics."""
       
       print("🔍 OpenScope Experimental Launcher Diagnostics")
       print("=" * 60)
       
       # System information
       import platform
       import psutil
       
       print(f"🖥️  System Information:")
       print(f"   OS: {platform.system()} {platform.release()}")
       print(f"   CPU: {psutil.cpu_count()} cores")
       print(f"   Memory: {psutil.virtual_memory().total / (1024**3):.1f} GB")
       print(f"   Python: {platform.python_version()}")
       
       # Check dependencies
       print(f"\n📦 Dependency Check:")
       
       dependencies = [
           ("numpy", "numpy"),
           ("pandas", "pandas"),
           ("psutil", "psutil"),
           ("requests", "requests")
       ]
       
       for name, module in dependencies:
           try:
               __import__(module)
               print(f"   ✅ {name}")
           except ImportError:
               print(f"   ❌ {name} - MISSING")
       
       # Check file system
       print(f"\n💾 File System Check:")
       
       critical_paths = [
           "C:/Program Files/Bonsai",
           "C:/ProgramData/AIBS_MPE",
           "C:/ExperimentData"
       ]
       
       for path in critical_paths:
           path_obj = Path(path)
           if path_obj.exists():
               if path_obj.is_dir():
                   try:
                       list(path_obj.iterdir())
                       print(f"   ✅ {path} (accessible)")
                   except PermissionError:
                       print(f"   ⚠️  {path} (permission denied)")
               else:
                   print(f"   ✅ {path} (file)")
           else:
               print(f"   ❌ {path} (missing)")
       
       # Test network
       print(f"\n🌐 Network Connectivity:")
       test_connectivity()
       
       # Test Git
       print(f"\n🔧 Git Configuration:")
       try:
           result = subprocess.run(
               ["git", "--version"],
               capture_output=True,
               text=True
           )
           if result.returncode == 0:
               print(f"   ✅ Git: {result.stdout.strip()}")
           else:
               print(f"   ❌ Git not found")
       except FileNotFoundError:
           print(f"   ❌ Git not installed")

Log Analysis Tools
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def analyze_experiment_logs(log_file):
       """Analyze experiment log files for common issues."""
       
       if not Path(log_file).exists():
           print(f"Log file not found: {log_file}")
           return
       
       with open(log_file, 'r') as f:
           lines = f.readlines()
       
       issues = {
           'errors': [],
           'warnings': [],
           'memory_issues': [],
           'network_issues': [],
           'bonsai_issues': []
       }
       
       for i, line in enumerate(lines, 1):
           line_lower = line.lower()
           
           # Categorize issues
           if 'error' in line_lower:
               issues['errors'].append((i, line.strip()))
           
           elif 'warning' in line_lower:
               issues['warnings'].append((i, line.strip()))
           
           elif any(term in line_lower for term in ['memory', 'out of memory', 'memory usage']):
               issues['memory_issues'].append((i, line.strip()))
           
           elif any(term in line_lower for term in ['network', 'connection', 'timeout', 'ssl']):
               issues['network_issues'].append((i, line.strip()))
           
           elif any(term in line_lower for term in ['bonsai', 'workflow', 'process terminated']):
               issues['bonsai_issues'].append((i, line.strip()))
       
       # Report findings
       print(f"📋 Log Analysis Results ({log_file}):")
       print(f"   Total lines: {len(lines)}")
       
       for category, items in issues.items():
           if items:
               print(f"\n   {category.upper()} ({len(items)}):")
               for line_num, content in items[:5]:  # Show first 5
                   print(f"     Line {line_num}: {content[:80]}...")
               if len(items) > 5:
                   print(f"     ... and {len(items) - 5} more")

Recovery Procedures
-------------------

Experiment Recovery
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def recover_failed_experiment(session_uuid, output_directory):
       """Attempt to recover data from a failed experiment."""
       
       print(f"🔄 Attempting recovery for session: {session_uuid}")
       
       recovery_info = {
           'session_uuid': session_uuid,
           'recovered_files': [],
           'partial_data': {},
           'recovery_success': False
       }
       
       # Search for files related to this session
       search_patterns = [
           f"*{session_uuid}*",
           f"*{session_uuid[:8]}*",  # Short UUID
           "session_*.pkl",
           "stimulus_*.csv",
           "*.json"
       ]
       
       output_path = Path(output_directory)
       if output_path.exists():
           for pattern in search_patterns:
               files = list(output_path.glob(pattern))
               recovery_info['recovered_files'].extend(files)
       
       # Analyze recovered files
       for file_path in recovery_info['recovered_files']:
           try:
               if file_path.suffix == '.json':
                   with open(file_path) as f:
                       data = json.load(f)
                       recovery_info['partial_data'][f'json_{file_path.name}'] = data
               
               elif file_path.suffix == '.csv':
                   import pandas as pd
                   df = pd.read_csv(file_path)
                   recovery_info['partial_data'][f'csv_{file_path.name}'] = {
                       'rows': len(df),
                       'columns': list(df.columns)
                   }
               
               elif file_path.suffix == '.pkl':
                   # Don't load pickle files directly for security
                   recovery_info['partial_data'][f'pkl_{file_path.name}'] = {
                       'size_bytes': file_path.stat().st_size
                   }
           
           except Exception as e:
               print(f"   Warning: Could not analyze {file_path}: {e}")
       
       recovery_info['recovery_success'] = len(recovery_info['recovered_files']) > 0
       
       return recovery_info

Environment Reset
~~~~~~~~~~~~~~~~~

.. code-block:: python

   def reset_experiment_environment():
       """Reset experiment environment to clean state."""
       
       print("🔄 Resetting experiment environment...")
       
       # Kill any running Bonsai processes
       import psutil
       
       for proc in psutil.process_iter(['pid', 'name']):
           if 'bonsai' in proc.info['name'].lower():
               try:
                   proc.terminate()
                   print(f"   Terminated Bonsai process (PID: {proc.info['pid']})")
               except (psutil.NoSuchProcess, psutil.AccessDenied):
                   pass
       
       # Clean temporary files
       temp_patterns = [
           "C:/temp/openscope_*",
           "C:/temp/bonsai_*",
           "./temp_*"
       ]
       
       cleaned_files = 0
       for pattern in temp_patterns:
           for file_path in glob.glob(pattern):
               try:
                   if Path(file_path).is_file():
                       Path(file_path).unlink()
                   else:
                       shutil.rmtree(file_path)
                   cleaned_files += 1
               except Exception as e:
                   print(f"   Warning: Could not clean {file_path}: {e}")
       
       print(f"   Cleaned {cleaned_files} temporary files")
       
       # Reset Git configuration if needed
       try:
           subprocess.run(["git", "config", "--global", "--unset", "http.sslVerify"], 
                         capture_output=True)
       except:
           pass
       
       print("✅ Environment reset complete")

Getting Help
------------

When reporting issues, please include:

1. **System Information:**
   - Operating system and version
   - Python version
   - OpenScope Experimental Launcher version

2. **Complete Error Messages:**
   - Full error traceback
   - Bonsai process output
   - Log file contents

3. **Parameter File:**
   - Anonymized parameter file that causes the issue

4. **Steps to Reproduce:**
   - Exact steps that lead to the problem
   - Whether the issue is reproducible

5. **Diagnostic Output:**
   - Run the diagnostic script and include output

**Diagnostic Script:**

.. code-block:: python

   # Save as diagnostic_report.py
   if __name__ == "__main__":
       print("Generating diagnostic report...")
       run_system_diagnostics()
       
       # Analyze recent logs
       log_files = [
           "experiment_debug.log",
           "openscope_launcher.log"
       ]
       
       for log_file in log_files:
           if Path(log_file).exists():
               analyze_experiment_logs(log_file)

**Contact Information:**

- GitHub Issues: `https://github.com/AllenNeuralDynamics/openscope-experimental-launcher/issues`
- Email Support: `openscope-support@alleninstitute.org`
- Documentation: `https://openscope-experimental-launcher.readthedocs.io`

**Before Contacting Support:**

1. Run the diagnostic script
2. Check the troubleshooting guide
3. Search existing GitHub issues
4. Try the suggested solutions
5. Test with minimal parameters