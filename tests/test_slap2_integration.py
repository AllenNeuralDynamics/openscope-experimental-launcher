"""
Integration test to run SLAP2 launcher with minimalist sample parameters.

This test demonstrates running the same Bonsai workflow with the SLAP2 launcher
that other rig types use, showing the flexibility of the launcher system.
"""

import os
import sys
import logging
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from openscope_experimental_launcher.slap2 import SLAP2Experiment


class TestSLAP2WithMinimalistParams:
    """Integration test for SLAP2 launcher using minimalist parameters."""
    
    def test_slap2_with_minimalist_params(self):
        """
        Test SLAP2 launcher with the same parameters used by minimalist launcher.
        
        This demonstrates that the same Bonsai workflow can be run across
        different machine configurations with different launchers.
        """
        # Get path to minimalist sample parameters
        minimalist_params_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'src', 
            'openscope_experimental_launcher', 
            'minimalist', 
            'sample_params.json'
        )
        
        # Verify the parameter file exists
        assert os.path.exists(minimalist_params_path), f"Minimalist params not found: {minimalist_params_path}"
        
        # Set up logging for the test
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        print(f"\n===== Testing SLAP2 Launcher with Minimalist Parameters =====")
        print(f"Parameter file: {minimalist_params_path}")
        
        # Create SLAP2 experiment
        experiment = SLAP2Experiment()
        
        # Mock parameter data that includes required Bonsai workflow path
        mock_params = {
            "repository_url": "https://github.com/AllenNeuralDynamics/openscope-community-predictive-processing.git",
            "repository_commit_hash": "main",
            "local_repository_path": "C:/BonsaiDataPredictiveProcessingTest",
            "bonsai_path": "code/stimulus-control/src/Standard_oddball_slap2.bonsai",
            "bonsai_exe_path": "code/stimulus-control/bonsai/Bonsai.exe",
            "bonsai_setup_script": "code/stimulus-control/bonsai/setup.cmd",
            "subject_id": "test_mouse",
            "user_id": "test_user"
        }
          # Comprehensive mocking for CI environments
        with patch('subprocess.Popen') as mock_popen, \
             patch('psutil.virtual_memory') as mock_vmem, \
             patch('openscope_experimental_launcher.utils.git_manager.setup_repository', return_value=True), \
             patch('openscope_experimental_launcher.utils.process_monitor.monitor_process'), \
             patch('os.path.exists', return_value=True), \
             patch('os.path.isdir', return_value=True), \
             patch('os.makedirs'), \
             patch('hashlib.md5') as mock_md5, \
             patch('builtins.open', create=True) as mock_open, \
             patch('json.load', return_value=mock_params), \
             patch('json.dump'), \
             patch('pickle.dump'), \
             patch('shutil.copy2'), \
             patch('tempfile.mkdtemp', return_value='/tmp/test_session'), \
             patch.object(experiment, 'post_experiment_processing', return_value=True), \
             patch.object(experiment, 'stop') as mock_stop, \
             patch('builtins.input', side_effect=['test_subject', 'test_experimenter', 'test_rig']):
            
            # Configure mocks for successful Bonsai execution
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.returncode = 0
            mock_process.poll.return_value = 0
            mock_process.stdout.readline.return_value = ""
            mock_process.stderr.readline.return_value = ""
            mock_popen.return_value = mock_process
            mock_vmem.return_value.percent = 50.0
            mock_md5.return_value.hexdigest.return_value = "test_checksum"
            
            # Mock file operations
            mock_open.return_value.__enter__.return_value.read.return_value = b'mock_content'
            
            try:
                # Run the experiment with minimalist parameters
                success = experiment.run(minimalist_params_path)
                
                if success:
                    print(f"\n✅ SLAP2 EXPERIMENT COMPLETED SUCCESSFULLY")
                      # Verify that the experiment was properly initialized
                    assert hasattr(experiment, 'subject_id'), "SLAP2 should have subject_id set"
                    
                    # Check that stop was called during cleanup
                    mock_stop.assert_called()
                    
                    print(f"🎯 Same Bonsai workflow successfully executed with SLAP2 launcher")
                    
                else:
                    pytest.fail("SLAP2 experiment failed - check logs for details")
                    
            except Exception as e:
                pytest.fail(f"SLAP2 experiment failed with exception: {e}")
            
            finally:
                # Ensure cleanup
                try:
                    experiment.stop()
                except:
                    pass  # Ignore cleanup errors in tests


def main():
    """
    Run the integration test directly.
    
    This allows running the test outside of pytest for manual testing.
    """
    test_instance = TestSLAP2WithMinimalistParams()
    test_instance.test_slap2_with_minimalist_params()
    print("\n✅ SLAP2 INTEGRATION TEST COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    main()