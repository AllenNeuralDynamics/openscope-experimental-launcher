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
        
        try:
            # Run the experiment with minimalist parameters
            success = experiment.run(minimalist_params_path)
            
            if success:
                print(f"\n✅ {rig_name} EXPERIMENT COMPLETED SUCCESSFULLY")
                print(f"Experiment data: {experiment.session_output_path}")
                
                # Check mindscope-specific outputs (pickle files)
                if hasattr(experiment, 'pickle_file_path') and experiment.pickle_file_path:
                    print(f"📦 Pickle file: {experiment.pickle_file_path}")
                    assert os.path.exists(experiment.pickle_file_path), f"{rig_name} pickle file should exist"
                    
                    # Get and display pickle data summary
                    if hasattr(experiment, 'get_pickle_data_summary'):
                        summary = experiment.get_pickle_data_summary()
                        print(f"📊 Data summary: {summary}")
                        
                        # Verify summary contains expected fields
                        assert 'rig_type' in summary, "Summary should contain rig_type"
                        assert 'session_uuid' in summary, "Summary should contain session_uuid"
                        assert 'mouse_id' in summary, "Summary should contain mouse_id"
                    
                else:
                    pytest.fail(f"{rig_name} experiment should generate a pickle file")
                
                print(f"🎯 Same Bonsai workflow successfully executed with {rig_name} launcher")
                
            else:
                pytest.fail(f"{rig_name} experiment failed - check logs for details")
                
        except Exception as e:
            pytest.fail(f"{rig_name} experiment failed with exception: {e}")
        
        finally:
            # Clean up
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