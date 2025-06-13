"""
Integration test to run SLAP2 launcher with minimalist sample parameters.

This test demonstrates running the same Bonsai workflow across different launchers
by using the SLAP2 launcher with the minimalist sample parameters.
"""

import os
import sys
import logging
import tempfile
import pytest

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from openscope_experimental_launcher.slap2.launcher import SLAP2Experiment


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
        
        try:
            # Run the experiment with minimalist parameters
            success = experiment.run(minimalist_params_path)
            
            if success:
                print(f"\n✅ SLAP2 EXPERIMENT COMPLETED SUCCESSFULLY")
                print(f"Experiment data: {experiment.session_output_path}")
                
                # Check SLAP2-specific outputs
                if hasattr(experiment, 'stimulus_table_path') and experiment.stimulus_table_path:
                    print(f"📊 Stimulus table: {experiment.stimulus_table_path}")
                    assert os.path.exists(experiment.stimulus_table_path), "Stimulus table file should exist"
                else:
                    print(f"⚠️  No stimulus table generated (expected if aind-data-schema not available)")
                
                if hasattr(experiment, 'session_json_path') and experiment.session_json_path:
                    print(f"📄 Session metadata: {experiment.session_json_path}")
                    assert os.path.exists(experiment.session_json_path), "Session JSON file should exist"
                else:
                    print(f"⚠️  No session.json generated (expected if aind-data-schema not available)")
                
                print(f"🎯 Same Bonsai workflow successfully executed with SLAP2 launcher")
                
            else:
                pytest.fail("SLAP2 experiment failed - check logs for details")
                
        except Exception as e:
            pytest.fail(f"SLAP2 experiment failed with exception: {e}")
        
        finally:
            # Clean up
            experiment.stop()


def main():
    """
    Run the integration test directly.
    
    This allows running the test outside of pytest for manual testing.
    """
    test_instance = TestSLAP2WithMinimalistParams()
    test_instance.test_slap2_with_minimalist_params()


if __name__ == "__main__":
    main()