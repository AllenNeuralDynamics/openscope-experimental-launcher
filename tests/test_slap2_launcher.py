"""
Unit tests for the SLAP2Experiment class.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from openscope_experimental_launcher.slap2.launcher import SLAP2Experiment


class TestSLAP2Experiment:
    """Test cases for SLAP2Experiment class."""

    def test_init(self):
        """Test SLAP2Experiment initialization."""
        experiment = SLAP2Experiment()
        
        assert experiment.session_type == "SLAP2"
        assert experiment.rig_id == "slap2_rig"
        assert experiment.experimenter_name == "Unknown"
        assert experiment.slap_fovs == []
        assert experiment.session_builder is not None
        assert experiment.stimulus_table_generator is not None

    def test_load_parameters_with_slap_fovs(self, param_file, sample_params, sample_slap_fovs):
        """Test parameter loading with SLAP FOV data."""
        experiment = SLAP2Experiment()
        
        # Add SLAP FOVs to parameters
        params_with_fovs = sample_params.copy()
        params_with_fovs["slap_fovs"] = sample_slap_fovs
        
        with patch.object(experiment.config_loader, 'load_config', return_value={}), \
             patch('json.load', return_value=params_with_fovs), \
             patch('builtins.open'), \
             patch('hashlib.md5') as mock_md5:
            
            mock_md5.return_value.hexdigest.return_value = "test_checksum"
            
            experiment.load_parameters(param_file)
        
        assert experiment.session_type == params_with_fovs["session_type"]
        assert experiment.rig_id == params_with_fovs["rig_id"]
        assert experiment.experimenter_name == params_with_fovs["experimenter_name"]

    @patch('openscope_experimental_launcher.slap2.launcher.AIND_SCHEMA_AVAILABLE', False)
    def test_parse_slap_fovs_no_schema(self, sample_slap_fovs):
        """Test SLAP FOV parsing when aind-data-schema is not available."""
        experiment = SLAP2Experiment()
        
        experiment._parse_slap_fovs(sample_slap_fovs)
        
        assert len(experiment.slap_fovs) == 0

    def test_create_bonsai_arguments_slap2(self):
        """Test SLAP2-specific Bonsai argument creation."""
        experiment = SLAP2Experiment()
        experiment.mouse_id = "test_mouse"
        experiment.session_uuid = "test-uuid"
        experiment.session_output_path = "/test/path/output.pkl"
        experiment.params = {
            "num_trials": 100,
            "laser_power": 15.0,
            "frame_rate": 30.0,
            "session_type": "SLAP2"
        }
        
        args = experiment.create_bonsai_arguments()
        
        assert "NumTrials=100" in args
        assert "LaserPower=15.00" in args
        assert "FrameRate=30.00" in args
        assert "SessionType=SLAP2" in args

    def test_create_stimulus_table_success(self, temp_dir):
        """Test successful stimulus table creation."""
        experiment = SLAP2Experiment()
        experiment.params = {"num_trials": 50}
        experiment.session_output_path = os.path.join(temp_dir, "output.pkl")
        
        with patch.object(experiment.stimulus_table_generator, 'generate_stimulus_table') as mock_gen:
            mock_gen.return_value = Mock()  # Mock DataFrame
            
            result = experiment.create_stimulus_table()
            
            assert result is True
            assert experiment.stimulus_table is not None
            mock_gen.assert_called_once()

    def test_create_stimulus_table_failure(self, temp_dir):
        """Test stimulus table creation failure."""
        experiment = SLAP2Experiment()
        experiment.params = {"num_trials": 50}
        experiment.session_output_path = os.path.join(temp_dir, "output.pkl")
        
        with patch.object(experiment.stimulus_table_generator, 'generate_stimulus_table') as mock_gen:
            mock_gen.return_value = None
            
            result = experiment.create_stimulus_table()
            
            assert result is False

    @patch('openscope_experimental_launcher.slap2.launcher.AIND_SCHEMA_AVAILABLE', False)
    def test_create_session_json_no_schema(self):
        """Test session.json creation when aind-data-schema is not available."""
        experiment = SLAP2Experiment()
        
        result = experiment.create_session_json()
        
        assert result is False

    def test_create_session_json_success(self, temp_dir):
        """Test successful session.json creation."""
        experiment = SLAP2Experiment()
        experiment.start_time = Mock()
        experiment.stop_time = Mock()
        experiment.params = {"session_type": "SLAP2"}
        experiment.mouse_id = "test_mouse"
        experiment.user_id = "test_user"
        experiment.experimenter_name = "Test Experimenter"
        experiment.session_uuid = "test-uuid"
        experiment.slap_fovs = []
        experiment.session_output_path = os.path.join(temp_dir, "output.pkl")
        
        mock_session = Mock()
        mock_session.write_standard_file = Mock()
        
        with patch.object(experiment.session_builder, 'build_session', return_value=mock_session):
            result = experiment.create_session_json()
            
            assert result is True
            mock_session.write_standard_file.assert_called_once()

    def test_create_session_json_failure(self, temp_dir):
        """Test session.json creation failure."""
        experiment = SLAP2Experiment()
        experiment.session_output_path = os.path.join(temp_dir, "output.pkl")
        
        with patch.object(experiment.session_builder, 'build_session', return_value=None):
            result = experiment.create_session_json()
            
            assert result is False

    def test_post_experiment_processing_success(self):
        """Test successful post-experiment processing."""
        experiment = SLAP2Experiment()
        
        with patch.object(experiment, 'create_stimulus_table', return_value=True), \
             patch.object(experiment, 'create_session_json', return_value=True):
            
            result = experiment.post_experiment_processing()
            
            assert result is True

    def test_post_experiment_processing_partial_failure(self):
        """Test post-experiment processing with partial failure."""
        experiment = SLAP2Experiment()
        
        with patch.object(experiment, 'create_stimulus_table', return_value=True), \
             patch.object(experiment, 'create_session_json', return_value=False):
            
            result = experiment.post_experiment_processing()
            
            assert result is False

    def test_run_success(self, param_file, mock_subprocess):
        """Test successful SLAP2 experiment run."""
        experiment = SLAP2Experiment()
        
        with patch.object(experiment, 'load_parameters') as mock_load, \
             patch.object(experiment.git_manager, 'setup_repository', return_value=True), \
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
        experiment = SLAP2Experiment()
        
        with patch.object(experiment, 'load_parameters'), \
             patch.object(experiment.git_manager, 'setup_repository', return_value=True), \
             patch.object(experiment, 'start_bonsai'), \
             patch('signal.signal'):
            
            mock_subprocess['process'].returncode = 1  # Failure
            experiment.bonsai_process = mock_subprocess['process']
            
            result = experiment.run(param_file)
            
            assert result is False

    def test_main_function_success(self, param_file):
        """Test the main function with successful execution."""
        with patch('sys.argv', ['script_name', param_file]), \
             patch('os.path.exists', return_value=True), \
             patch('openscope_experimental_launcher.slap2.launcher.SLAP2Experiment') as mock_class:
            
            mock_experiment = Mock()
            mock_experiment.run.return_value = True
            mock_experiment.stimulus_table_path = "test_table.csv"
            mock_experiment.session_json_path = "test_session.json"
            mock_experiment.output_path = "test_output.pkl"
            mock_class.return_value = mock_experiment
            
            with pytest.raises(SystemExit) as exc_info:
                from openscope_experimental_launcher.slap2.launcher import main
                main()
            
            assert exc_info.value.code == 0

    def test_main_function_file_not_found(self):
        """Test the main function with parameter file not found."""
        with patch('sys.argv', ['script_name', 'nonexistent.json']), \
             patch('os.path.exists', return_value=False):
            
            with pytest.raises(SystemExit) as exc_info:
                from openscope_experimental_launcher.slap2.launcher import main
                main()
            
            assert exc_info.value.code == 1