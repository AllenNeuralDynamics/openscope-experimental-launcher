"""
Tests for Bonsai interface module.
"""

import pytest
import subprocess
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock

from src.openscope_experimental_launcher.interfaces import bonsai_interface


class TestBonsaiInterface:
    """Test cases for Bonsai interface functions."""

    def test_setup_bonsai_environment_success(self):
        """Test successful Bonsai environment setup."""
        params = {'bonsai_exe_path': 'bonsai.exe'}
        
        with patch.object(bonsai_interface, 'check_installation', return_value=True):
            result = bonsai_interface.setup_bonsai_environment(params)
            assert result is True

    def test_setup_bonsai_environment_failure(self):
        """Test Bonsai environment setup failure."""
        params = {'bonsai_exe_path': 'bonsai.exe'}
        
        with patch.object(bonsai_interface, 'check_installation', return_value=False):
            result = bonsai_interface.setup_bonsai_environment(params)
            assert result is False

    def test_setup_bonsai_environment_no_exe_path(self):
        """Test Bonsai environment setup without exe path."""
        params = {}
        
        with patch.object(bonsai_interface, 'check_installation', return_value=True):
            result = bonsai_interface.setup_bonsai_environment(params)
            assert result is True

    def test_check_installation_success(self):
        """Test successful Bonsai installation check."""
        mock_result = Mock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result):
            result = bonsai_interface.check_installation('bonsai.exe')
            assert result is True

    def test_check_installation_failure_returncode(self):
        """Test Bonsai installation check with non-zero return code."""
        mock_result = Mock()
        mock_result.returncode = 1
        
        with patch('subprocess.run', return_value=mock_result):
            result = bonsai_interface.check_installation('bonsai.exe')
            assert result is False

    def test_check_installation_timeout(self):
        """Test Bonsai installation check with timeout."""
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('bonsai.exe', 30)):
            result = bonsai_interface.check_installation('bonsai.exe')
            assert result is False

    def test_check_installation_file_not_found(self):
        """Test Bonsai installation check with file not found."""
        with patch('subprocess.run', side_effect=FileNotFoundError):
            result = bonsai_interface.check_installation('bonsai.exe')
            assert result is False

    def test_check_installation_os_error(self):
        """Test Bonsai installation check with OS error."""
        with patch('subprocess.run', side_effect=OSError):
            result = bonsai_interface.check_installation('bonsai.exe')
            assert result is False

    def test_construct_bonsai_arguments_basic(self):
        """Test basic Bonsai argument construction."""
        params = {}
        args = bonsai_interface.construct_bonsai_arguments(params)
        assert isinstance(args, list)
        assert '--no-editor' in args

    def test_construct_bonsai_arguments_with_editor(self):
        """Test Bonsai argument construction with editor enabled."""
        params = {'enable_editor': True}
        args = bonsai_interface.construct_bonsai_arguments(params)
        assert '--no-editor' not in args

    def test_construct_bonsai_arguments_with_custom_args(self):
        """Test Bonsai argument construction with custom arguments."""
        params = {'script_arguments': ['--verbose', '--debug']}
        args = bonsai_interface.construct_bonsai_arguments(params)
        
        assert '--verbose' in args
        assert '--debug' in args
        assert '--no-editor' in args

    def test_construct_bonsai_arguments_with_properties(self):
        """Test Bonsai argument construction with properties."""
        params = {'properties': {'Property1': 'value1', 'Property2': 'value2'}}
        args = bonsai_interface.construct_bonsai_arguments(params)
        
        assert '-p' in args
        prop_index = args.index('-p')
        assert 'Property1=value1' in args[prop_index + 1]
        assert 'Property2=value2' in args[prop_index + 1]

    def test_construct_bonsai_arguments_with_layout(self):
        """Test Bonsai argument construction with layout file."""
        params = {'layout_file': 'test_layout.bonsai.layout'}
        args = bonsai_interface.construct_bonsai_arguments(params)
        
        assert '--layout' in args
        layout_index = args.index('--layout')
        assert args[layout_index + 1] == 'test_layout.bonsai.layout'

    def test_start_bonsai_workflow_success(self):
        """Test successful Bonsai workflow startup."""
        mock_process = MagicMock()
        
        with patch('subprocess.Popen', return_value=mock_process) as mock_popen, \
             patch('os.path.exists', return_value=True):
            process = bonsai_interface.start_bonsai_workflow(
                'test_workflow.bonsai',
                'bonsai.exe',
                arguments=['--no-editor'],
                properties={'Property1': 'value1'},
                output_path='C:/output'
            )
            
            assert process == mock_process
            mock_popen.assert_called_once()

    def test_start_bonsai_workflow_file_not_found(self):
        """Test Bonsai workflow startup with missing file."""
        with patch('os.path.exists', return_value=False):
            with pytest.raises(FileNotFoundError):
                bonsai_interface.start_bonsai_workflow('nonexistent.bonsai')

    def test_start_bonsai_workflow_subprocess_error(self):
        """Test Bonsai workflow startup with subprocess error."""
        with patch('os.path.exists', return_value=True), \
             patch('subprocess.Popen', side_effect=OSError("Failed to start process")):
            with pytest.raises(OSError):
                bonsai_interface.start_bonsai_workflow('test_workflow.bonsai')

    def test_start_bonsai_workflow_default_exe(self):
        """Test Bonsai workflow startup with default executable."""
        mock_process = MagicMock()
        
        with patch('subprocess.Popen', return_value=mock_process) as mock_popen, \
             patch('os.path.exists', return_value=True):
            process = bonsai_interface.start_bonsai_workflow('test_workflow.bonsai')
            
            assert process == mock_process
            mock_popen.assert_called_once()
            
            # Check that default bonsai executable was used
            call_args = mock_popen.call_args[0][0]
            assert any('bonsai' in str(arg).lower() for arg in call_args)

    def test_start_bonsai_workflow_with_properties(self):
        """Test Bonsai workflow startup with properties."""
        mock_process = MagicMock()
        
        with patch('subprocess.Popen', return_value=mock_process) as mock_popen, \
             patch('os.path.exists', return_value=True):
            properties = {'Property1': 'value1', 'Property2': 'value2'}
            process = bonsai_interface.start_bonsai_workflow(
                'test_workflow.bonsai',
                properties=properties
            )
            
            assert process == mock_process
            mock_popen.assert_called_once()
            
            # Check that properties were passed
            call_args = mock_popen.call_args[0][0]
            assert '-p' in call_args

    def test_start_bonsai_workflow_with_output_path(self):
        """Test Bonsai workflow startup with output path."""
        mock_process = MagicMock()
        
        with patch('subprocess.Popen', return_value=mock_process) as mock_popen, \
             patch('os.path.exists', return_value=True):
            process = bonsai_interface.start_bonsai_workflow(
                'test_workflow.bonsai',
                output_path='/test/output'
            )
            
            assert process == mock_process
            mock_popen.assert_called_once()
            
            # Check that working directory was set
            call_kwargs = mock_popen.call_args[1]
            assert 'cwd' in call_kwargs
            assert call_kwargs['cwd'] == '/test/output'

    def test_validate_workflow_file_success(self):
        """Test successful workflow file validation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bonsai', delete=False) as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n<WorkflowBuilder>\n</WorkflowBuilder>')
            temp_path = f.name
        
        try:
            result = bonsai_interface.validate_workflow_file(temp_path)
            assert result is True
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_validate_workflow_file_not_found(self):
        """Test workflow file validation with missing file."""
        result = bonsai_interface.validate_workflow_file('nonexistent.bonsai')
        assert result is False

    def test_validate_workflow_file_invalid_xml(self):
        """Test workflow file validation with invalid XML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bonsai', delete=False) as f:
            f.write('invalid xml content')
            temp_path = f.name
        
        try:
            result = bonsai_interface.validate_workflow_file(temp_path)
            assert result is False
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_validate_workflow_file_not_bonsai_workflow(self):
        """Test workflow file validation with valid XML but not Bonsai workflow."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bonsai', delete=False) as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n<NotWorkflowBuilder>\n</NotWorkflowBuilder>')
            temp_path = f.name
        
        try:
            result = bonsai_interface.validate_workflow_file(temp_path)
            assert result is False
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_extract_workflow_properties_success(self):
        """Test successful workflow properties extraction."""
        workflow_content = '''<?xml version="1.0" encoding="utf-8"?>
        <WorkflowBuilder>
          <Workflow>
            <Nodes>
              <Expression xsi:type="ExternalizedProperty">
                <Name>Property1</Name>
                <Value>DefaultValue1</Value>
              </Expression>
              <Expression xsi:type="ExternalizedProperty">
                <Name>Property2</Name>
                <Value>DefaultValue2</Value>
              </Expression>
            </Nodes>
          </Workflow>
        </WorkflowBuilder>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bonsai', delete=False) as f:
            f.write(workflow_content)
            temp_path = f.name
        
        try:
            properties = bonsai_interface.extract_workflow_properties(temp_path)
            assert properties is not None
            assert 'Property1' in properties
            assert 'Property2' in properties
            assert properties['Property1'] == 'DefaultValue1'
            assert properties['Property2'] == 'DefaultValue2'
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_extract_workflow_properties_file_not_found(self):
        """Test workflow properties extraction with missing file."""
        properties = bonsai_interface.extract_workflow_properties('nonexistent.bonsai')
        assert properties is None

    def test_extract_workflow_properties_invalid_xml(self):
        """Test workflow properties extraction with invalid XML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bonsai', delete=False) as f:
            f.write('invalid xml content')
            temp_path = f.name
        
        try:
            properties = bonsai_interface.extract_workflow_properties(temp_path)
            assert properties is None
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_create_layout_file_success(self):
        """Test successful layout file creation."""
        layout_data = {
            'EditorSettings': {
                'Visible': True,
                'Location': {'X': 100, 'Y': 200},
                'Size': {'Width': 800, 'Height': 600}
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bonsai.layout', delete=False) as f:
            temp_path = f.name
        
        try:
            os.unlink(temp_path)  # Remove the temp file so we can test creation
            result = bonsai_interface.create_layout_file(temp_path, layout_data)
            assert result is True
            assert os.path.exists(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_create_layout_file_failure(self):
        """Test layout file creation failure."""
        layout_data = {'test': 'data'}
        invalid_path = '/invalid/path/that/does/not/exist/layout.bonsai.layout'
        
        result = bonsai_interface.create_layout_file(invalid_path, layout_data)
        assert result is False

    def test_parse_bonsai_output_success(self):
        """Test successful Bonsai output parsing."""
        output_lines = [
            'Bonsai starting...',
            'Workflow loaded successfully',
            'Processing frame 1',
            'Processing frame 2',
            'Workflow completed'
        ]
        
        parsed_output = bonsai_interface.parse_bonsai_output(output_lines)
        
        assert parsed_output is not None
        assert 'status' in parsed_output
        assert 'frames_processed' in parsed_output
        assert parsed_output['frames_processed'] == 2

    def test_parse_bonsai_output_with_errors(self):
        """Test Bonsai output parsing with errors."""
        output_lines = [
            'Bonsai starting...',
            'Error: Could not load workflow',
            'Exception: Test exception'
        ]
        
        parsed_output = bonsai_interface.parse_bonsai_output(output_lines)
        
        assert parsed_output is not None
        assert 'status' in parsed_output
        assert 'errors' in parsed_output
        assert len(parsed_output['errors']) > 0

    def test_parse_bonsai_output_empty(self):
        """Test Bonsai output parsing with empty output."""
        parsed_output = bonsai_interface.parse_bonsai_output([])
        
        assert parsed_output is not None
        assert 'status' in parsed_output
        assert parsed_output['status'] == 'no_output'

    def test_monitor_bonsai_process_success(self):
        """Test successful Bonsai process monitoring."""
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.stdout.readline.side_effect = [
            b'Workflow started\n',
            b'Processing...\n',
            b''  # End of output
        ]
        
        with patch('time.sleep'):
            result = bonsai_interface.monitor_bonsai_process(mock_process, timeout=1)
            
            assert result is not None
            assert 'output_lines' in result

    def test_monitor_bonsai_process_timeout(self):
        """Test Bonsai process monitoring with timeout."""
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.stdout.readline.return_value = b'Processing...\n'
        
        with patch('time.sleep'), \
             patch('time.time', side_effect=[0, 1, 2, 3]):  # Simulate timeout
            result = bonsai_interface.monitor_bonsai_process(mock_process, timeout=2)
            
            assert result is not None
            assert 'timeout' in result
