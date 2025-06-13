"""
Process monitoring utilities for OpenScope experimental launchers.

Handles process monitoring, memory usage tracking, and runaway process detection.
"""

import time
import logging
import psutil
from typing import Callable, Optional
import subprocess


class ProcessMonitor:
    """
    Handles process monitoring with memory usage tracking and runaway detection.
    """
    
    def __init__(self, kill_threshold: float = 90.0):
        """
        Initialize the process monitor.
        
        Args:
            kill_threshold: Memory usage threshold (percentage) above initial usage
                          that triggers process termination
        """
        self.kill_threshold = kill_threshold
    
    def monitor_process(self, 
                       process: subprocess.Popen, 
                       initial_memory_percent: float,
                       kill_callback: Optional[Callable] = None):
        """
        Monitor a process until it completes or exceeds memory threshold.
        
        Args:
            process: The subprocess to monitor
            initial_memory_percent: Initial memory usage percentage
            kill_callback: Function to call if process needs to be killed
        """
        logging.info("Starting process monitoring...")
        
        try:
            # Get process object for monitoring
            try:
                ps_process = psutil.Process(process.pid)
            except psutil.NoSuchProcess:
                logging.warning("Process ended unexpectedly")
                return
            
            # Monitor process until completion
            while process.poll() is None:
                try:
                    # Check system memory usage
                    vmem = psutil.virtual_memory()
                    current_memory_percent = vmem.percent
                    
                    # Check if memory usage exceeds threshold
                    if current_memory_percent > initial_memory_percent + self.kill_threshold:
                        logging.warning(
                            f"Detected runaway process, memory usage: {current_memory_percent}% "
                            f"(threshold: {initial_memory_percent + self.kill_threshold}%)"
                        )
                        
                        if kill_callback:
                            kill_callback()
                        else:
                            self._kill_process(process)
                        break
                    
                    # Log periodic memory status
                    if hasattr(self, '_last_memory_log'):
                        if time.time() - self._last_memory_log > 60:  # Log every minute
                            logging.debug(f"Memory usage: {current_memory_percent}%")
                            self._last_memory_log = time.time()
                    else:
                        self._last_memory_log = time.time()
                
                except Exception as e:
                    logging.warning(f"Error checking process status: {e}")
                
                # Sleep before next check
                time.sleep(0.5)
        
        except Exception as e:
            logging.error(f"Error in process monitoring: {e}")
    
    def _kill_process(self, process: subprocess.Popen):
        """
        Kill a process and its children.
        
        Args:
            process: The subprocess to kill
        """
        try:
            logging.warning(f"Killing process {process.pid}")
            process.kill()
            
            # Try to kill child processes on Windows
            try:
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)])
            except Exception as e:
                logging.warning(f"Could not kill child processes: {e}")
                
        except Exception as e:
            logging.error(f"Error killing process: {e}")
    
    def get_process_memory_info(self, process: subprocess.Popen) -> dict:
        """
        Get detailed memory information for a process.
        
        Args:
            process: The subprocess to inspect
            
        Returns:
            Dictionary containing memory information
        """
        try:
            ps_process = psutil.Process(process.pid)
            memory_info = ps_process.memory_info()
            memory_percent = ps_process.memory_percent()
            
            return {
                'rss': memory_info.rss,  # Resident Set Size
                'vms': memory_info.vms,  # Virtual Memory Size
                'percent': memory_percent,
                'available': psutil.virtual_memory().available,
                'total': psutil.virtual_memory().total
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logging.warning(f"Could not get memory info for process: {e}")
            return {}
    
    def is_process_responsive(self, process: subprocess.Popen, timeout: float = 5.0) -> bool:
        """
        Check if a process is responsive by testing if it responds within timeout.
        
        Args:
            process: The subprocess to check
            timeout: Timeout in seconds
            
        Returns:
            True if process is responsive, False otherwise
        """
        try:
            # Try to get process status
            ps_process = psutil.Process(process.pid)
            status = ps_process.status()
            
            # Check if process is in a good state
            if status in [psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING]:
                return True
            elif status in [psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD]:
                return False
            else:
                # For other states, assume responsive for now
                logging.debug(f"Process in state: {status}")
                return True
                
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
        except Exception as e:
            logging.warning(f"Error checking process responsiveness: {e}")
            return True  # Assume responsive if we can't check