"""
Comprehensive tests targeting under-covered code to reach 65% coverage.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import tempfile
import os
import subprocess
import datetime
import psutil

# Import modules to test
from src.openscope_experimental_launcher.utils import git_manager, process_monitor, session_builder, stimulus_table
from src.openscope_experimental_launcher.interfaces import bonsai_interface, python_interface
from src.openscope_experimental_launcher.launchers import matlab_launcher, python_launcher


class TestComprehensiveCoverage:
    """Comprehensive tests to boost coverage to 65%."""
    
    # Python Interface Tests (35% coverage -> target higher)
    def test_python_interface_create_process_basic(self):
        """Test Python interface process creation."""
        params = {
            'script_path': 'test_script.py',
            'script_parameters': {'param1': 'value1'}
        }
        
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_popen.return_value = mock_process
            
            result = python_interface.create_python_process(params, 'python')
            
            assert result == mock_process
            mock_popen.assert_called_once()
    
    def test_python_interface_construct_arguments(self):
        """Test Python argument construction."""
        params = {
            'script_path': 'test_script.py',
            'script_parameters': {'param1': 'value1', 'param2': 'value2'}
        }
        
        args = python_interface.construct_python_arguments(params)
        
        assert 'test_script.py' in args
        assert '--param1' in args
        assert 'value1' in args
        assert '--param2' in args
        assert 'value2' in args
    
    def test_python_interface_validate_params_missing_script(self):
        """Test parameter validation with missing script."""
        params = {}
        
        with pytest.raises(ValueError, match="script_path"):
            python_interface.validate_python_parameters(params)
    
    def test_python_interface_validate_params_valid(self):
        """Test parameter validation with valid params."""
        params = {'script_path': 'test_script.py'}
        
        # Should not raise
        python_interface.validate_python_parameters(params)
    
    def test_python_interface_get_executable_path(self):
        """Test Python executable path retrieval."""
        result = python_interface.get_python_executable_path('python')
        assert result == 'python'
        
        result = python_interface.get_python_executable_path(None)
        assert result == 'python'
    
    def test_python_interface_process_arguments_with_env(self):
        """Test process arguments with environment variables."""
        params = {
            'script_path': 'test.py',
            'environment_variables': {'VAR1': 'value1', 'VAR2': 'value2'}
        }
        
        args = python_interface.construct_python_arguments(params)
        assert 'test.py' in args
        
    # Matlab and Python Launcher Tests (very low coverage)
    def test_matlab_launcher_create_process(self):
        """Test Matlab launcher process creation."""
        params = {
            'script_path': 'test_script.m',
            'matlab_executable': 'matlab'
        }
        
        with patch('src.openscope_experimental_launcher.interfaces.matlab_interface.create_matlab_process') as mock_create:
            mock_process = Mock()
            mock_create.return_value = mock_process
            
            launcher = matlab_launcher.MatlabLauncher()
            result = launcher.create_process(params)
            
            assert result == mock_process
            mock_create.assert_called_once_with(params, 'matlab')
    
    def test_python_launcher_create_process(self):
        """Test Python launcher process creation."""
        params = {
            'script_path': 'test_script.py',
            'python_executable': 'python'
        }
        
        with patch('src.openscope_experimental_launcher.interfaces.python_interface.create_python_process') as mock_create:
            mock_process = Mock()
            mock_create.return_value = mock_process
            
            launcher = python_launcher.PythonLauncher()
            result = launcher.create_process(params)
            
            assert result == mock_process
            mock_create.assert_called_once_with(params, 'python')
    
    # Git Manager Tests (58% coverage -> target higher)
    def test_git_manager_get_repo_name_various_formats(self):
        """Test repo name extraction with various URL formats."""
        assert git_manager._get_repo_name_from_url('https://github.com/user/repo.git') == 'repo'
        assert git_manager._get_repo_name_from_url('https://github.com/user/repo') == 'repo'
        assert git_manager._get_repo_name_from_url('git@github.com:user/repo.git') == 'repo'
        assert git_manager._get_repo_name_from_url('repo.git') == 'repo'
    
    def test_git_manager_check_git_available_false(self):
        """Test git availability check when git is not available."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()
            result = git_manager._check_git_available()
            assert result is False
    
    def test_git_manager_force_remove_error(self):
        """Test force remove directory with error."""
        with patch('shutil.rmtree', side_effect=OSError("Permission denied")):
            result = git_manager._force_remove_directory('/test/path')
            assert result is False
    
    def test_git_manager_current_commit_hash_success(self):
        """Test getting current commit hash successfully."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = 'abc123def456\n'
        
        with patch('subprocess.run', return_value=mock_result):
            result = git_manager._get_current_commit_hash('/test/path')
            assert result == 'abc123def456'
    
    def test_git_manager_current_commit_hash_error(self):
        """Test getting current commit hash with error."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = 'Not a git repository'
        
        with patch('subprocess.run', return_value=mock_result):
            result = git_manager._get_current_commit_hash('/test/path')
            assert result is None
    
    def test_git_manager_checkout_commit_nonexistent_path(self):
        """Test checkout commit with nonexistent path."""
        with patch('os.path.exists', return_value=False):
            result = git_manager._checkout_commit('/nonexistent', 'abc123')
            assert result is False
    
    def test_git_manager_clone_repository_existing_dir(self):
        """Test clone repository when directory already exists."""
        with patch('os.path.exists', return_value=True):
            result = git_manager._clone_repository('https://test.git', '/existing/path')
            assert result is False
    
    # Session Builder Tests (55% coverage -> target higher)
    def test_session_builder_build_session_no_schema(self):
        """Test session building when schema is not available."""
        with patch('src.openscope_experimental_launcher.utils.session_builder.AIND_SCHEMA_AVAILABLE', False):
            result = session_builder.build_session()
            assert result is None
    
    def test_session_builder_get_additional_script_parameters(self):
        """Test getting additional script parameters."""
        params = {'extra_param': 'extra_value', 'script_parameters': {'param1': 'value1'}}
        
        result = session_builder.get_additional_script_parameters(params, 'test_rig')
        
        assert isinstance(result, dict)
        # Should include extra params but not script_parameters
        assert 'extra_param' in result
        assert 'script_parameters' not in result
    
    def test_session_builder_create_session_notes(self):
        """Test session notes creation."""
        params = {'notes': 'Custom notes'}
        
        notes = session_builder.create_session_notes(params, 'subject123', 'user456', 'test_rig')
        
        assert isinstance(notes, str)
        assert 'subject123' in notes
        assert 'user456' in notes
        assert 'test_rig' in notes
    
    def test_session_builder_get_script_name(self):
        """Test script name generation."""
        result = session_builder.get_script_name('SLAP2')
        assert 'SLAP2' in result
        
        result = session_builder.get_script_name('Generic')
        assert 'Generic' in result
    
    # Stimulus Table Tests (78% coverage -> target remaining gaps)
    def test_stimulus_table_load_from_file_missing(self):
        """Test loading stimulus table from missing file."""
        with patch('os.path.exists', return_value=False):
            result = stimulus_table.load_stimulus_table('/nonexistent/file.pkl')
            assert result is None
    
    def test_stimulus_table_load_from_file_error(self):
        """Test loading stimulus table with error."""
        with patch('os.path.exists', return_value=True), \
             patch('pickle.load', side_effect=Exception("Load error")):
            result = stimulus_table.load_stimulus_table('/test/file.pkl')
            assert result is None
    
    def test_stimulus_table_save_to_file_error(self):
        """Test saving stimulus table with error."""
        table = Mock()
        with patch('pickle.dump', side_effect=Exception("Save error")):
            result = stimulus_table.save_stimulus_table(table, '/test/file.pkl')
            assert result is False
    
    def test_stimulus_table_create_from_params_with_stim_table(self):
        """Test creating stimulus table from params with existing stim_table."""
        params = {
            'stim_table': [[1, 2, 3], [4, 5, 6]],
            'column_names': ['col1', 'col2', 'col3']
        }
        
        table = stimulus_table.create_stimulus_table_from_params(params)
        
        assert table is not None
        assert len(table) == 2
    
    def test_stimulus_table_validate_table_invalid(self):
        """Test stimulus table validation with invalid table."""
        # Test None
        assert stimulus_table.validate_stimulus_table(None) is False
        
        # Test empty
        assert stimulus_table.validate_stimulus_table([]) is False
        
        # Test non-list
        assert stimulus_table.validate_stimulus_table("not a list") is False
    
    def test_stimulus_table_get_column_names_from_table(self):
        """Test getting column names from table."""
        table = [
            {'col1': 1, 'col2': 2, 'col3': 3},
            {'col1': 4, 'col2': 5, 'col3': 6}
        ]
        
        columns = stimulus_table.get_column_names(table)
        
        assert 'col1' in columns
        assert 'col2' in columns
        assert 'col3' in columns
        assert len(columns) == 3
    
    def test_stimulus_table_get_column_names_empty(self):
        """Test getting column names from empty table."""
        columns = stimulus_table.get_column_names([])
        assert columns == []
    
    # Bonsai Interface Tests (48% coverage -> target uncovered areas)
    def test_bonsai_interface_verify_packages_success(self):
        """Test package verification with successful verification."""
        config_content = '''
        <packages>
            <package id="TestPackage" version="1.0.0" />
        </packages>
        '''
        
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=config_content)), \
             patch('src.openscope_experimental_launcher.interfaces.bonsai_interface.get_installed_packages') as mock_get:
            mock_get.return_value = {'TestPackage': '1.0.0'}
            
            result = bonsai_interface.verify_packages('config.xml', '/test/dir')
            
            assert result is True
    
    def test_bonsai_interface_get_bonsai_exe_path_custom(self):
        """Test getting Bonsai executable path with custom path."""
        custom_path = 'C:\\Custom\\Bonsai.exe'
        
        with patch('os.path.exists', return_value=True):
            result = bonsai_interface.get_bonsai_exe_path(custom_path)
            assert result == custom_path
    
    def test_bonsai_interface_get_bonsai_exe_path_default(self):
        """Test getting Bonsai executable path with default search."""
        with patch('os.path.exists', side_effect=lambda p: 'Bonsai.exe' in p), \
             patch('os.path.join', side_effect=lambda *args: '\\'.join(args)):
            result = bonsai_interface.get_bonsai_exe_path()
            assert result is not None
    
    def test_bonsai_interface_install_bonsai_not_found(self):
        """Test Bonsai installation with script not found."""
        with patch('os.path.exists', return_value=False):
            result = bonsai_interface.install_bonsai('/nonexistent/install.bat')
            assert result is False
    
    def test_bonsai_interface_install_bonsai_success(self):
        """Test successful Bonsai installation."""
        mock_result = Mock()
        mock_result.returncode = 0
        
        with patch('os.path.exists', return_value=True), \
             patch('subprocess.run', return_value=mock_result):
            result = bonsai_interface.install_bonsai('/test/install.bat')
            assert result is True
    
    def test_bonsai_interface_start_workflow_with_args(self):
        """Test starting workflow with arguments."""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_popen.return_value = mock_process
            
            result = bonsai_interface.start_workflow(
                '/test/workflow.bonsai', 
                '/test/bonsai.exe',
                arguments=['--arg1', 'value1'],
                output_path='/test/output'
            )
            
            assert result == mock_process
            mock_popen.assert_called_once()
    
    # Process Monitor Tests (71% coverage -> target remaining gaps)
    def test_process_monitor_memory_info_exception_handling(self):
        """Test memory info with proper exception handling."""
        mock_process = Mock()
        mock_process.pid = 1234
        
        with patch('psutil.Process', side_effect=Exception("Process error")):
            result = process_monitor.get_process_memory_info(mock_process)
            assert result == {}
    
    def test_process_monitor_is_responsive_no_such_process(self):
        """Test process responsiveness check with no such process."""
        mock_process = Mock()
        mock_process.pid = 9999
        
        with patch('psutil.Process', side_effect=psutil.NoSuchProcess(9999)):
            result = process_monitor.is_process_responsive(mock_process)
            assert result is False
    
    def test_process_monitor_is_responsive_access_denied(self):
        """Test process responsiveness check with access denied."""
        mock_process = Mock()
        mock_process.pid = 1234
        
        with patch('psutil.Process', side_effect=psutil.AccessDenied(1234)):
            result = process_monitor.is_process_responsive(mock_process)
            assert result is False
    
    def test_process_monitor_get_process_cpu_usage(self):
        """Test getting process CPU usage."""
        mock_process = Mock()
        mock_process.pid = 1234
        
        mock_ps_process = Mock()
        mock_ps_process.cpu_percent.return_value = 15.5
        
        with patch('psutil.Process', return_value=mock_ps_process):
            result = process_monitor.get_process_cpu_usage(mock_process)
            assert result == 15.5
    
    def test_process_monitor_get_process_cpu_usage_error(self):
        """Test getting process CPU usage with error."""
        mock_process = Mock()
        mock_process.pid = 1234
        
        with patch('psutil.Process', side_effect=Exception("CPU error")):
            result = process_monitor.get_process_cpu_usage(mock_process)
            assert result == 0.0


def mock_open(read_data=''):
    """Helper function to create a mock for file opening."""
    m = MagicMock()
    m.__enter__.return_value = MagicMock()
    m.__enter__.return_value.read.return_value = read_data
    return m
