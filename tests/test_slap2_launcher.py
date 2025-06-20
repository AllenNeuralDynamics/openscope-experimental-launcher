"""
Unit tests for the SLAP2Launcher class.
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add the scripts directory to the path for SLAP2Launcher
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import sys
from pathlib import Path

# Add scripts directory to path for importing
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from slap2_launcher import SLAP2Launcher


class TestSLAP2Launcher:
    """Test cases for SLAP2Launcher class."""
    
    def test_init(self):
        """Test SLAP2Launcher initialization."""
        experiment = SLAP2Launcher()
        
        assert experiment.session_type == "SLAP2"
        assert hasattr(experiment, 'slap_fovs')
        assert experiment.slap_fovs == []
        # Test that stimulus table can be created using functional approach
        assert hasattr(experiment, 'stimulus_table')
    
    def test_load_parameters_with_slap_fovs(self, param_file, sample_params, sample_slap_fovs):
        """Test parameter loading with SLAP FOV data."""
        experiment = SLAP2Launcher()
        
        # Add SLAP FOVs to parameters
        params_with_fovs = sample_params.copy()
        params_with_fovs["slap_fovs"] = sample_slap_fovs
        
        with patch('openscope_experimental_launcher.utils.config_loader.load_config', return_value={}), \
             patch('json.load', return_value=params_with_fovs), \
             patch('builtins.open'), \
             patch('hashlib.md5') as mock_md5:
            
            mock_md5.return_value.hexdigest.return_value = "test_checksum"
            experiment.load_parameters(param_file)
        
        assert experiment.session_type == params_with_fovs["session_type"]
        assert experiment.user_id == params_with_fovs["user_id"]
    
    @patch('openscope_experimental_launcher.slap2.launcher.AIND_SCHEMA_AVAILABLE', False)
    def test_slap2_no_schema_available(self):
        """Test SLAP2 experiment when aind-data-schema is not available."""
        experiment = SLAP2Launcher()
        
        # When schema is not available, experiment should still work
        assert experiment is not None
        # Test that stimulus table functionality exists through functional approach
        assert hasattr(experiment, 'stimulus_table')
    
    def test_create_bonsai_arguments_slap2(self):
        """Test SLAP2-specific Bonsai argument creation with real workflow parameters."""
        from openscope_experimental_launcher.interfaces import bonsai_interface
        
        experiment = SLAP2Launcher()
        experiment.subject_id = "test_mouse"
        experiment.session_uuid = "test-uuid"
        experiment.params = {
            "script_parameters": {
                "PortName": "COM3",
                "OutputFolder": "C:/TestData",
                "Subject": "test_subject",
                "NbMismatchPerCondition": 5,
                "NbBaselineGrating": 15,
            }        }
        
        args = bonsai_interface.create_bonsai_property_arguments(experiment.params)
        
        assert "-p" in args
        args_str = " ".join(args)
        assert "PortName=COM3" in args_str
        assert "OutputFolder=C:/TestData" in args_str
        assert "Subject=test_subject" in args_str
        assert "NbMismatchPerCondition=5" in args_str
        assert "NbBaselineGrating=15" in args_str
    
    def test_generate_stimulus_table_success(self, temp_dir):
        """Test successful stimulus table generation."""
        experiment = SLAP2Launcher()
        experiment.params = {"num_trials": 50}
        experiment.session_directory = temp_dir
        
        with patch('openscope_experimental_launcher.utils.stimulus_table.generate_slap2_stimulus_table') as mock_gen:
            mock_gen.return_value = Mock()  # Mock DataFrame
            
            result = experiment._generate_stimulus_table()
            
            assert result is True
            mock_gen.assert_called_once()

    def test_generate_stimulus_table_failure(self, temp_dir):
        """Test stimulus table generation failure."""
        experiment = SLAP2Launcher()
        experiment.params = {"num_trials": 50}
        experiment.session_directory = temp_dir
        
        with patch('openscope_experimental_launcher.utils.stimulus_table.generate_slap2_stimulus_table') as mock_gen:
            mock_gen.return_value = None
            
            result = experiment._generate_stimulus_table()
            
            assert result is False

    @patch('openscope_experimental_launcher.slap2.launcher.AIND_SCHEMA_AVAILABLE', False)
    def test_create_session_json_no_schema(self):
        """Test session.json creation when aind-data-schema is not available."""
        experiment = SLAP2Launcher()
        
        result = experiment.create_session_json()
        
        assert result is False

    def test_create_session_json_success(self, temp_dir):
        """Test successful session.json creation."""
        experiment = SLAP2Launcher()
        experiment.start_time = Mock()
        experiment.stop_time = Mock()
        experiment.params = {"session_type": "SLAP2"}
        experiment.subject_id = "test_mouse"
        experiment.user_id = "test_user"
        experiment.user_id = "Test User"
        experiment.session_uuid = "test-uuid"
        experiment.slap_fovs = []
        experiment.session_directory = temp_dir
        
        mock_session = Mock()
        mock_session.write_standard_file = Mock()
        
        with patch('openscope_experimental_launcher.utils.session_builder.build_slap2_session', return_value=mock_session):
            result = experiment.create_session_json()
            
            assert result is True
            mock_session.write_standard_file.assert_called_once()

    def test_create_session_json_failure(self, temp_dir):
        """Test session.json creation failure."""
        experiment = SLAP2Launcher()
        experiment.session_directory = temp_dir
        
        with patch('openscope_experimental_launcher.utils.session_builder.build_slap2_session', return_value=None):
            result = experiment.create_session_json()
            
            assert result is False

    def test_post_experiment_processing_success(self):
        """Test successful post-experiment processing."""
        experiment = SLAP2Launcher()
        
        with patch.object(experiment, 'create_stimulus_table', return_value=True), \
             patch.object(experiment, 'create_session_json', return_value=True):
            
            result = experiment.post_experiment_processing()
            
            assert result is True

    def test_post_experiment_processing_partial_failure(self):
        """Test post-experiment processing with partial failure."""
        experiment = SLAP2Launcher()
        
        with patch.object(experiment, 'create_stimulus_table', return_value=True), \
             patch.object(experiment, 'create_session_json', return_value=False):
            
            result = experiment.post_experiment_processing()
            
            assert result is False

    def test_run_success(self, param_file, mock_subprocess):
        """Test successful SLAP2 experiment run."""
        experiment = SLAP2Launcher()
        
        with patch.object(experiment, 'load_parameters') as mock_load, \
             patch('openscope_experimental_launcher.utils.git_manager.setup_repository', return_value=True), \
             patch.object(experiment, 'start_bonsai'), \
             patch.object(experiment, 'post_experiment_processing', return_value=True), \
             patch('signal.signal'):
            
            mock_subprocess['process'].returncode = 0
            experiment.bonsai_process = mock_subprocess['process']
            
            result = experiment.run(param_file)
            
            assert result is True
            mock_load.assert_called_once_with(param_file)

    def test_run_bonsai_failure(self, param_file, mock_subprocess):
        """Test SLAP2 experiment run with Bonsai failure."""
        experiment = SLAP2Launcher()
        
        with patch.object(experiment, 'load_parameters'), \
             patch('openscope_experimental_launcher.utils.git_manager.setup_repository', return_value=True), \
             patch.object(experiment, 'start_bonsai'), \
             patch('signal.signal'):
            
            mock_subprocess['process'].returncode = 1  # Failure
            experiment.bonsai_process = mock_subprocess['process']
            
            result = experiment.run(param_file)
            
            assert result is False

    @pytest.mark.skip(reason="main function not implemented in current launcher")
    def test_main_function_success(self, param_file):
        """Test the main function with successful execution."""
        with patch('sys.argv', ['script_name', param_file]), \
             patch('os.path.exists', return_value=True), \
             patch('openscope_experimental_launcher.slap2.launcher.SLAP2Launcher') as mock_class:
            
            mock_experiment = Mock()
            mock_experiment.run.return_value = True
            mock_experiment.stimulus_table_path = "test_table.csv"
            mock_experiment.session_json_path = "test_session.json"
            mock_experiment.output_path = "test_output.pkl"
            mock_class.return_value = mock_experiment
            
            with pytest.raises(SystemExit) as exc_info:
                # Import main from the scripts directory  
                sys.path.insert(0, str(scripts_dir))
                import slap2_launcher
                slap2_launcher.main()
            
            assert exc_info.value.code == 0

    @pytest.mark.skip(reason="main function not implemented in current launcher")
    def test_main_function_file_not_found(self):
        """Test the main function with parameter file not found."""
        with patch('sys.argv', ['script_name', 'nonexistent.json']), \
             patch('os.path.exists', return_value=False):
            
            with pytest.raises(SystemExit) as exc_info:
                # Import main from the scripts directory  
                sys.path.insert(0, str(scripts_dir))
                import slap2_launcher
                slap2_launcher.main()
            
            assert exc_info.value.code == 1
