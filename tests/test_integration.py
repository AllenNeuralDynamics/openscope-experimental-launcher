"""
Integration tests for the complete workflow.
"""

import os
import pytest
import tempfile
import json
from unittest.mock import Mock, patch
from openscope_experimental_launcher import BaseExperiment, SLAP2Experiment


@pytest.mark.integration
class TestWorkflowIntegration:
    """Integration tests for complete workflows."""

    def test_base_experiment_end_to_end(self, temp_dir):
        """Test complete BaseExperiment workflow."""
        # Create mock workflow file first
        workflow_file = os.path.join(temp_dir, "test_workflow.bonsai")
        with open(workflow_file, 'w') as f:
            f.write("<WorkflowBuilder>Test Workflow</WorkflowBuilder>")
        
        # Create mock Bonsai executable
        bonsai_exe = os.path.join(temp_dir, "mock_bonsai.exe")
        with open(bonsai_exe, 'w') as f:
            f.write("mock executable")
        
        # Create test parameter file with absolute path
        params = {
            "subject_id": "integration_test_mouse",
            "user_id": "integration_test_user",
            "bonsai_path": workflow_file,  # Use absolute path
            "bonsai_exe_path": os.path.join(temp_dir, "mock_bonsai.exe"),  # Add mock executable
            "output_directory": temp_dir
        }
        
        param_file = os.path.join(temp_dir, "test_params.json")
        with open(param_file, 'w') as f:
            json.dump(params, f)
        
        experiment = BaseExperiment()
        
        # Mock subprocess to simulate Bonsai execution
        with patch('subprocess.Popen') as mock_popen, \
             patch('psutil.virtual_memory') as mock_vmem, \
             patch('openscope_experimental_launcher.utils.git_manager.setup_repository', return_value=True), \
             patch('openscope_experimental_launcher.utils.process_monitor.monitor_process'):
            
            # Configure mocks
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.returncode = 0
            mock_process.poll.return_value = 0
            mock_process.stdout.readline.return_value = ""
            mock_process.stderr.readline.return_value = ""
            mock_popen.return_value = mock_process
            
            mock_vmem.return_value.percent = 50.0
              # Run experiment
            result = experiment.run(param_file)
            
            assert result is True
            assert experiment.subject_id == params["subject_id"]
            assert experiment.user_id == params["user_id"]
            assert experiment.bonsai_process is not None

    @pytest.mark.integration
    def test_slap2_experiment_end_to_end(self, temp_dir):
        """Test complete SLAP2Experiment workflow with metadata generation."""
        # Create mock workflow file first
        workflow_file = os.path.join(temp_dir, "slap2_workflow.bonsai")
        with open(workflow_file, 'w') as f:
            f.write("<WorkflowBuilder>SLAP2 Test Workflow</WorkflowBuilder>")
        
        # Create mock Bonsai executable
        bonsai_exe = os.path.join(temp_dir, "mock_bonsai.exe")
        with open(bonsai_exe, 'w') as f:
            f.write("mock executable")
        
        # Create comprehensive test parameters with absolute path
        params = {
            "subject_id": "slap2_test_mouse",
            "user_id": "slap2_test_user",
            "user_id": "Integration Tester",
            "session_type": "SLAP2",
            "rig_id": "test_slap2_rig",
            "num_trials": 20,
            "laser_power": 12.0,
            "laser_wavelength": 920,
            "frame_rate": 30.0,
            "bonsai_path": workflow_file,  # Use absolute path
            "bonsai_exe_path": bonsai_exe,  # Add mock executable
            "output_directory": temp_dir,
            "slap_fovs": [{
                "index": 0,
                "imaging_depth": 100,
                "targeted_structure": "VISp",  # Use valid CCF structure
                "fov_coordinate_ml": 2.0,
                "fov_coordinate_ap": -2.5
            }]
        }
        
        param_file = os.path.join(temp_dir, "slap2_params.json")
        with open(param_file, 'w') as f:
            json.dump(params, f)
        
        experiment = SLAP2Experiment()
          # Mock subprocess and post-processing
        with patch('subprocess.Popen') as mock_popen, \
             patch('psutil.virtual_memory') as mock_vmem, \
             patch('openscope_experimental_launcher.utils.git_manager.setup_repository', return_value=True), \
             patch('openscope_experimental_launcher.utils.process_monitor.monitor_process'), \
             patch.object(experiment, 'post_experiment_processing', return_value=True):
            
            # Configure mocks
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.returncode = 0
            mock_process.poll.return_value = 0
            mock_process.stdout.readline.return_value = ""
            mock_process.stderr.readline.return_value = ""
            mock_popen.return_value = mock_process
            
            mock_vmem.return_value.percent = 50.0
              # Run experiment
            result = experiment.run(param_file)
            
            assert result is True
            assert experiment.session_type == "SLAP2"
            assert experiment.user_id == "Integration Tester"

    @pytest.mark.integration
    @pytest.mark.requires_git
    def test_git_repository_integration(self, temp_dir):
        """Test Git repository management integration."""
        from openscope_experimental_launcher.utils import git_manager
          # Skip if Git is not available
        if not git_manager._check_git_available():
            pytest.skip("Git not available for integration testing")
        
        # Test repository setup with local path
        params = {
            'repository_url': 'https://github.com/octocat/Hello-World.git',
            'repository_commit_hash': 'main',
            'local_repository_path': temp_dir
        }
          # This test requires internet connection, so we'll mock it
        with patch.object(git_manager, '_clone_repository', return_value=True), \
             patch('os.path.exists', return_value=False):
            
            result = git_manager.setup_repository(params)
            assert result is True

    @pytest.mark.integration
    def test_config_loader_integration(self, temp_dir):
        """Test configuration loading integration."""
        from openscope_experimental_launcher.utils import config_loader
        
        # Create test config file
        config_content = """
[Behavior]
subject_id = integration_test
user_id = test_user
nidevice = Dev1

[Stim]
fps = 60.0
monitor_brightness = 50
"""
        config_path = os.path.join(temp_dir, "test_config.cfg")
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        params = {"config_path": config_path}
        config = config_loader.load_config(params)
        
        assert "Behavior" in config
        assert "Stim" in config
        assert config["Behavior"]["subject_id"] == "integration_test"
        assert config["Stim"]["fps"] == 60.0

    @pytest.mark.integration
    def test_stimulus_table_generation_integration(self, temp_dir):
        """Test stimulus table generation integration."""
        from openscope_experimental_launcher.utils import stimulus_table
        import pandas as pd
        
        # Create mock Bonsai output
        bonsai_output = pd.DataFrame({
            'trial_index': range(10),
            'stimulus_start_time': [i * 2.0 for i in range(10)],
            'stimulus_end_time': [i * 2.0 + 1.0 for i in range(10)],
            'stimulus_type': ['standard' if i % 5 != 0 else 'oddball' for i in range(10)]
        })
        
        bonsai_file = os.path.join(temp_dir, "trials.csv")
        bonsai_output.to_csv(bonsai_file, index=False)
        
        params = {"num_trials": 10}
        session_output_path = os.path.join(temp_dir, "output.pkl")
        
        # Generate stimulus table
        result = stimulus_table.generate_slap2_stimulus_table(params, session_output_path)
        
        assert result is not None
        assert len(result) >= 10
        assert 'trial_index' in result.columns
        assert 'stimulus_type' in result.columns
        
        # Test statistics calculation
        stats = stimulus_table.get_trial_statistics(result)
        assert stats['total_trials'] >= 10
        assert 'trial_types' in stats

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skip(reason="create_stimulus_table implementation depends on session_output_path which no longer exists")
    def test_full_workflow_with_file_generation(self, temp_dir):
        """Test complete workflow with actual file generation."""
        # This is a slow test that generates actual output files
        
        experiment = SLAP2Experiment()
        
        params = {
            "subject_id": "full_test_mouse",
            "user_id": "full_test_user",
            "session_type": "SLAP2",
            "num_trials": 5,  # Keep small for speed
            "bonsai_path": "test.bonsai",
            "output_directory": temp_dir
        }
        
        param_file = os.path.join(temp_dir, "full_test_params.json")
        with open(param_file, 'w') as f:
            json.dump(params, f)
        
        # Create minimal workflow file
        workflow_file = os.path.join(temp_dir, "test.bonsai")
        with open(workflow_file, 'w') as f:
            f.write("<WorkflowBuilder>Minimal Test</WorkflowBuilder>")
        
        # Load parameters (without running Bonsai)
        experiment.load_parameters(param_file)
        
        # Note: Output path setup is now handled automatically in _prepare_bonsai_parameters
        
        # Test stimulus table generation
        result = experiment.create_stimulus_table()
        assert result is True
        assert experiment.stimulus_table_path is not None
        assert os.path.exists(experiment.stimulus_table_path)
        
        # Verify stimulus table content
        import pandas as pd
        stimulus_df = pd.read_csv(experiment.stimulus_table_path)
        assert len(stimulus_df) == 5
        assert 'trial_index' in stimulus_df.columns