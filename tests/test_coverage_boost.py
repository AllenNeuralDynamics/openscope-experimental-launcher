"""
Focused coverage boost tests for the lowest-coverage modules.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
import datetime
import tempfile

# Import the modules we want to improve coverage for
from openscope_experimental_launcher.base.bonsai_interface import BonsaiInterface
from openscope_experimental_launcher.utils.process_monitor import ProcessMonitor


class TestBonsaiInterfaceBasic:
    """Basic tests for BonsaiInterface to boost coverage."""
    
    @patch('os.path.exists')
    def test_check_installation(self, mock_exists):
        """Test installation checking."""
        interface = BonsaiInterface()
        interface.set_bonsai_path("C:/Bonsai/Bonsai.exe")
        
        # Test when Bonsai exe exists
        mock_exists.return_value = True
        assert interface.check_installation() is True
        
        # Test when Bonsai exe doesn't exist
        mock_exists.return_value = False
        assert interface.check_installation() is False

    @patch('os.path.isdir', return_value=True)
    @patch('os.listdir')
    @patch('os.path.exists')
    def test_get_installed_packages(self, mock_exists, mock_listdir, mock_isdir):
        """Test getting installed packages."""
        interface = BonsaiInterface()
        interface.set_bonsai_path("C:/Bonsai/Bonsai.exe")
        
        # Test when packages directory exists
        mock_exists.return_value = True
        mock_listdir.return_value = ["Bonsai.Core.1.0.0", "Bonsai.Vision.2.1.0", "InvalidName"]
        
        packages = interface.get_installed_packages()
        expected = {"Bonsai.Core": "1.0.0", "Bonsai.Vision": "2.1.0"}
        assert packages == expected

    @patch('subprocess.Popen')
    @patch('os.path.exists')
    @patch('os.chdir')
    @patch('os.getcwd')
    def test_install_bonsai(self, mock_getcwd, mock_chdir, mock_exists, mock_popen):
        """Test Bonsai installation."""
        interface = BonsaiInterface()
        interface.set_bonsai_path("C:/Bonsai/Bonsai.exe")
        
        mock_getcwd.return_value = "/original/dir"
        
        # Test missing setup script
        mock_exists.return_value = False
        result = interface.install_bonsai("missing_setup.exe")
        assert result is False
        
        # Test successful installation
        mock_exists.return_value = True
        mock_process = Mock()
        mock_process.stdout.readline.side_effect = ["Installing...\n", ""]
        mock_process.stderr.read.return_value = ""
        mock_process.wait.return_value = 0
        mock_process.poll.return_value = 0
        mock_popen.return_value = mock_process
        
        with patch.object(interface, 'check_installation', return_value=True):
            result = interface.install_bonsai("setup.exe")
            assert result is True

    @patch('xml.etree.ElementTree.parse')
    @patch('os.path.exists')
    def test_parse_bonsai_config(self, mock_exists, mock_parse):
        """Test Bonsai config parsing."""
        interface = BonsaiInterface()
        
        # Test missing file
        mock_exists.return_value = False
        result = interface.parse_bonsai_config("missing.config")
        assert result == {}
        
        # Test XML parsing error
        mock_exists.return_value = True
        mock_parse.side_effect = Exception("Parse error")
        result = interface.parse_bonsai_config("invalid.config")
        assert result == {}

    def test_version_utilities(self):
        """Test version comparison utilities."""
        interface = BonsaiInterface()
        
        # Test _normalize_version - it removes trailing .0s
        assert interface._normalize_version("1.0.0") == "1"  # Removes trailing .0s
        assert interface._normalize_version("1.2.0") == "1.2"
        assert interface._normalize_version("1.2.3") == "1.2.3"
        
        # Test _versions_match
        assert interface._versions_match("1.0.0", "1.0.0") is True
        assert interface._versions_match("1.0", "1.0.0") is True  # Normalized comparison
        assert interface._versions_match("2.0.0", "1.0.0") is False

class TestProcessMonitorBasic:
    """Basic tests for ProcessMonitor to boost coverage."""
    
    @patch('time.sleep')
    @patch('psutil.virtual_memory')
    @patch('psutil.Process')
    def test_monitor_process(self, mock_psutil_process, mock_vmem, mock_sleep):
        """Test basic process monitoring."""
        monitor = ProcessMonitor(kill_threshold=20.0)
        
        # Mock process that completes successfully
        mock_process = Mock()
        mock_process.poll.side_effect = [None, None, 0]  # Running then complete
        mock_process.returncode = 0
        mock_process.pid = 12345
        
        # Mock psutil process
        mock_ps_proc = Mock()
        mock_psutil_process.return_value = mock_ps_proc
        
        # Mock safe memory usage
        mock_vmem.return_value.percent = 50.0
        
        kill_callback = Mock()
        monitor.monitor_process(mock_process, 40.0, kill_callback)
        
        # Should complete without killing
        kill_callback.assert_not_called()

    def test_get_process_memory_info(self):
        """Test process memory info retrieval."""
        monitor = ProcessMonitor()
        
        # Mock process
        mock_process = Mock()
        mock_process.pid = 12345
        
        with patch('psutil.Process') as mock_psutil_process, \
             patch('psutil.virtual_memory') as mock_vmem:
            
            # Mock successful process info
            mock_proc = Mock()
            mock_proc.memory_info.return_value = Mock(rss=1024*1024, vms=2048*1024)
            mock_proc.memory_percent.return_value = 25.0
            mock_psutil_process.return_value = mock_proc
            
            mock_vmem.return_value = Mock(available=8*1024*1024*1024, total=16*1024*1024*1024)
            
            info = monitor.get_process_memory_info(mock_process)
            
            assert "rss" in info
            assert "percent" in info
            assert info["percent"] == 25.0

    def test_is_process_responsive(self):
        """Test process responsiveness checking."""
        monitor = ProcessMonitor()
        
        # Mock process
        mock_process = Mock()
        mock_process.pid = 12345
        
        with patch('psutil.Process') as mock_psutil_process:
            # Test responsive process
            mock_proc = Mock()
            mock_proc.status.return_value = "running"
            mock_psutil_process.return_value = mock_proc
            
            result = monitor.is_process_responsive(mock_process)
            assert result is True
            
            # Test unresponsive process  
            mock_proc.status.return_value = "zombie"
            result = monitor.is_process_responsive(mock_process)
            assert result is False