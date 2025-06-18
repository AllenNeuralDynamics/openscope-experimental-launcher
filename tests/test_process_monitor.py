"""
Unit tests for the ProcessMonitor utility class.
"""

import time
import pytest
import psutil
import subprocess
from unittest.mock import Mock, patch, MagicMock
from openscope_experimental_launcher.utils.process_monitor import ProcessMonitor


class TestProcessMonitor:
    """Test cases for ProcessMonitor class."""
    
    def test_init_default_threshold(self):
        """Test ProcessMonitor initialization with default threshold."""
        monitor = ProcessMonitor()
        assert monitor.kill_threshold == 90.0
    
    def test_init_custom_threshold(self):
        """Test ProcessMonitor initialization with custom threshold."""
        monitor = ProcessMonitor(kill_threshold=80.0)
        assert monitor.kill_threshold == 80.0
    
    @patch('psutil.Process')
    @patch('time.sleep')
    def test_monitor_process_normal_completion(self, mock_sleep, mock_process_class):
        """Test monitoring a process that completes normally."""
        # Setup mocks
        mock_process = Mock()
        mock_process.pid = 1234
        mock_process.poll.return_value = 0  # Process completed
        
        mock_ps_process = Mock()
        mock_ps_process.memory_percent.return_value = 50.0
        mock_ps_process.is_running.return_value = False
        mock_process_class.return_value = mock_ps_process
        
        # Test monitoring
        monitor = ProcessMonitor()
        monitor.monitor_process(mock_process, 45.0)
        
        # Verify process was checked
        mock_process_class.assert_called_with(1234)
    
    @patch('psutil.Process')
    @patch('time.sleep')
    def test_monitor_process_no_such_process(self, mock_sleep, mock_process_class):
        """Test monitoring when process ends unexpectedly."""
        mock_process = Mock()
        mock_process.pid = 1234
        
        mock_process_class.side_effect = psutil.NoSuchProcess(1234)
        
        monitor = ProcessMonitor()
        monitor.monitor_process(mock_process, 45.0)
        
        # Should handle the exception gracefully
        mock_process_class.assert_called_with(1234)
    
    @patch('psutil.Process')
    @patch('time.sleep')
    def test_monitor_process_memory_exceeded(self, mock_sleep, mock_process_class):
        """Test monitoring when memory usage exceeds threshold."""
        # Setup mocks
        mock_process = Mock()
        mock_process.pid = 1234
        mock_process.poll.return_value = None  # Process still running        
        mock_ps_process = Mock()
        mock_ps_process.memory_percent.return_value = 95.0  # High memory usage
        mock_ps_process.is_running.return_value = True
        mock_process_class.return_value = mock_ps_process
        
        # Mock kill callback
        mock_kill_callback = Mock()
        
        monitor = ProcessMonitor(kill_threshold=40.0)  # Lower threshold to ensure trigger
        
        # Mock virtual memory to return high usage
        with patch('psutil.virtual_memory') as mock_virtual_memory:
            mock_memory = Mock()
            mock_memory.percent = 95.0  # High system memory usage
            mock_virtual_memory.return_value = mock_memory
            
            # Mock the sleep to avoid infinite loop
            def side_effect_sleep(duration):
                # After first sleep, make process appear to have ended
                mock_process.poll.return_value = 0
                mock_ps_process.is_running.return_value = False
            
            mock_sleep.side_effect = side_effect_sleep
            
            monitor.monitor_process(mock_process, 45.0, kill_callback=mock_kill_callback)
        
        # Verify kill callback was called
        mock_kill_callback.assert_called_once()
    
    @patch('psutil.Process')
    @patch('time.sleep')
    def test_monitor_process_access_denied(self, mock_sleep, mock_process_class):
        """Test monitoring when access to process is denied."""
        mock_process = Mock()
        mock_process.pid = 1234
        mock_process.poll.return_value = None
        
        mock_ps_process = Mock()
        mock_ps_process.memory_percent.side_effect = psutil.AccessDenied(1234)
        mock_ps_process.is_running.return_value = True
        mock_process_class.return_value = mock_ps_process
          # Mock to end process after first iteration
        def side_effect_sleep(duration):
            mock_process.poll.return_value = 0
            mock_ps_process.is_running.return_value = False
        
        mock_sleep.side_effect = side_effect_sleep
        
        monitor = ProcessMonitor()
        monitor.monitor_process(mock_process, 45.0)
        
        # Test should complete without raising exception
    
    @patch('psutil.Process')
    def test_get_process_memory_info_normal(self, mock_process_class):
        """Test getting process memory info."""
        mock_ps_process = Mock()
        mock_ps_process.memory_info.return_value = Mock(rss=1024*1024*10)  # 10MB
        mock_ps_process.memory_percent.return_value = 15.5
        mock_process_class.return_value = mock_ps_process
        
        monitor = ProcessMonitor()
        mock_process = Mock()
        mock_process.pid = 1234
        info = monitor.get_process_memory_info(mock_process)
        
        assert 'rss' in info
        assert 'percent' in info
        assert info['percent'] == 15.5
    
    @patch('psutil.Process')
    def test_get_process_memory_info_exception(self, mock_process_class):
        """Test getting process memory info when process access fails."""
        mock_process_class.side_effect = psutil.NoSuchProcess(1234)
        
        monitor = ProcessMonitor()
        mock_process = Mock()
        mock_process.pid = 1234
        info = monitor.get_process_memory_info(mock_process)
        
        assert info == {}  # Returns empty dict on exception
    
    @patch('psutil.Process')
    def test_is_process_responsive_normal(self, mock_process_class):
        """Test checking if process is responsive."""
        mock_ps_process = Mock()
        mock_ps_process.status.return_value = psutil.STATUS_RUNNING  # Process is running
        mock_process_class.return_value = mock_ps_process
        
        monitor = ProcessMonitor()
        mock_process = Mock()
        mock_process.pid = 1234
        mock_process.poll.return_value = None  # Still running
        result = monitor.is_process_responsive(mock_process)
        
        assert result is True
    
    @patch('psutil.Process')
    def test_is_process_responsive_not_running(self, mock_process_class):
        """Test checking if process is responsive when it's not running."""
        mock_ps_process = Mock()
        mock_ps_process.status.return_value = psutil.STATUS_DEAD  # Set status to DEAD
        mock_process_class.return_value = mock_ps_process
        
        monitor = ProcessMonitor()
        mock_process = Mock()
        mock_process.pid = 1234
        mock_process.poll.return_value = 0  # Process has ended
        result = monitor.is_process_responsive(mock_process)
        
        assert result is False
