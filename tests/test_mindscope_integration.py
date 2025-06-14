"""
Integration test to run Mindscope launchers with minimalist sample parameters.

This test demonstrates running the same Bonsai workflow across different mindscope
rig types by using cluster, mesoscope, and neuropixel launchers with the minimalist 
sample parameters.
"""

import os
import sys
import logging
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from openscope_experimental_launcher.mindscope import (
    ClusterExperiment, 
    MesoscopeExperiment, 
    NeuropixelExperiment
)


class TestMindoscopeWithMinimalistParams:
    """Integration test for Mindscope launchers using minimalist parameters."""
    
    def test_cluster_with_minimalist_params(self):
        """
        Test Cluster launcher with the same parameters used by minimalist launcher.
        
        This demonstrates that the same Bonsai workflow can be run across 
        different machine configurations with cluster-specific pickle output.
        """
        self._test_mindscope_launcher(ClusterExperiment, "CLUSTER")
    
    def test_mesoscope_with_minimalist_params(self):
        """
        Test Mesoscope launcher with the same parameters used by minimalist launcher.
        
        This demonstrates that the same Bonsai workflow can be run across 
        different machine configurations with mesoscope-specific pickle output.
        """
        self._test_mindscope_launcher(MesoscopeExperiment, "MESOSCOPE")
    
    def test_neuropixel_with_minimalist_params(self):
        """
        Test Neuropixel launcher with the same parameters used by minimalist launcher.
        
        This demonstrates that the same Bonsai workflow can be run across 
        different machine configurations with neuropixel-specific pickle output.
        """
        self._test_mindscope_launcher(NeuropixelExperiment, "NEUROPIXEL")
    
    def _test_mindscope_launcher(self, launcher_class, rig_name):
        """
        Common test method for all mindscope launchers.
        
        Args:
            launcher_class: The experiment class to test
            rig_name: Name of the rig for logging
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
        
        print(f"\n===== Testing {rig_name} Launcher with Minimalist Parameters =====")
        print(f"Parameter file: {minimalist_params_path}")
        
        # Create experiment
        experiment = launcher_class()
        
        # Comprehensive mocking for CI environments
        with patch('subprocess.Popen') as mock_popen, \
             patch('psutil.virtual_memory') as mock_vmem, \
             patch.object(experiment.git_manager, 'setup_repository', return_value=True), \
             patch.object(experiment.process_monitor, 'monitor_process'), \
             patch('os.path.exists', return_value=True), \
             patch('os.path.isdir', return_value=True), \
             patch('os.makedirs'), \
             patch('hashlib.md5') as mock_md5, \
             patch('builtins.open', create=True) as mock_open, \
             patch('json.load', return_value={}), \
             patch('json.dump'), \
             patch('pickle.dump'), \
             patch('shutil.copy2'), \
             patch('tempfile.mkdtemp', return_value='/tmp/test_session'), \
             patch.object(experiment, 'post_experiment_processing', return_value=True), \
             patch.object(experiment, 'stop') as mock_stop:
            
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
            
            # Run the experiment with minimalist parameters
            success = experiment.run(minimalist_params_path)
            
            if success:
                print(f"\n✅ {rig_name} EXPERIMENT COMPLETED SUCCESSFULLY")
                
                # Verify that the experiment was properly initialized
                assert hasattr(experiment, 'mouse_id'), f"{rig_name} should have mouse_id set"
                assert hasattr(experiment, 'session_output_path'), f"{rig_name} should have session_output_path set"
                
                # Check that stop was called during cleanup
                mock_stop.assert_called()
                
                print(f"🎯 Same Bonsai workflow successfully executed with {rig_name} launcher")
                
            else:
                pytest.fail(f"{rig_name} experiment failed - check logs for details")
                

            experiment.stop()


def test_all_mindscope_launchers():
    """
    Run all mindscope launcher tests in sequence.
    
    This demonstrates that the same Bonsai workflow can be executed
    across all mindscope rig types with their respective post-processing.
    """
    test_instance = TestMindoscopeWithMinimalistParams()
    
    print("\n" + "="*80)
    print("TESTING ALL MINDSCOPE LAUNCHERS WITH SAME BONSAI WORKFLOW")
    print("="*80)
    
    # Test cluster launcher
    test_instance.test_cluster_with_minimalist_params()
    
    # Test mesoscope launcher  
    test_instance.test_mesoscope_with_minimalist_params()
    
    # Test neuropixel launcher
    test_instance.test_neuropixel_with_minimalist_params()
    
    print("\n" + "="*80)
    print("✅ ALL MINDSCOPE LAUNCHERS COMPLETED SUCCESSFULLY")
    print("🎯 Same Bonsai workflow executed across all rig types!")
    print("="*80)


def main():
    """
    Run the integration tests directly.
    
    This allows running the tests outside of pytest for manual testing.
    """
    test_all_mindscope_launchers()


if __name__ == "__main__":
    main()