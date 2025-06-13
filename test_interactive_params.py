#!/usr/bin/env python3
"""
Test script to demonstrate the new interactive parameter collection functionality.

This script shows how the launcher now prompts for subject_id and operator_name
at runtime instead of requiring them in the JSON parameter file.
"""

import sys
import os
import tempfile
import json

# Add the src directory to the path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from openscope_experimental_launcher.base.experiment import BaseExperiment
from openscope_experimental_launcher.slap2.launcher import SLAP2Experiment


def create_test_parameter_file():
    """Create a test parameter file without subject/experimenter info."""
    test_params = {
        "repository_url": "https://github.com/AllenNeuralDynamics/openscope-community-predictive-processing.git",
        "bonsai_path": "code/stimulus-control/src/Standard_oddball_slap2.bonsai",
        "output_directory": tempfile.mkdtemp(),
        "session_type": "test_session"
    }
    
    # Create temporary parameter file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(test_params, temp_file, indent=2)
    temp_file.close()
    
    return temp_file.name


def test_base_experiment():
    """Test the BaseExperiment with interactive prompts."""
    print("=== Testing BaseExperiment ===")
    print("The system will now prompt for:")
    print("1. Subject ID")
    print("2. Experimenter name")
    print()
    
    param_file = create_test_parameter_file()
    experiment = BaseExperiment()
    
    try:
        # This will trigger the interactive prompts
        experiment.load_parameters(param_file)
        
        print(f"\nCollected Information:")
        print(f"Subject ID: {experiment.mouse_id}")
        print(f"Experimenter: {experiment.user_id}")
        print(f"Parameters loaded from: {param_file}")
        
    finally:
        # Clean up
        os.unlink(param_file)


def test_slap2_experiment():
    """Test the SLAP2Experiment with extended interactive prompts."""
    print("\n=== Testing SLAP2Experiment ===")
    print("The system will now prompt for:")
    print("1. Subject ID")
    print("2. Experimenter name")
    print("3. Rig ID (with default shown)")
    print()
    
    param_file = create_test_parameter_file()
    experiment = SLAP2Experiment()
    
    try:
        # This will trigger the interactive prompts
        experiment.load_parameters(param_file)
        
        print(f"\nCollected Information:")
        print(f"Subject ID: {experiment.mouse_id}")
        print(f"Experimenter: {experiment.user_id}")
        print(f"Rig ID: {experiment.rig_id}")
        print(f"Parameters loaded from: {param_file}")
        
    finally:
        # Clean up
        os.unlink(param_file)


if __name__ == "__main__":
    print("Interactive Parameter Collection Test")
    print("=" * 40)
    print("\nThis test demonstrates the new runtime parameter collection.")
    print("You'll be prompted to enter information that was previously")
    print("required in the JSON parameter file.")
    print()
    
    choice = input("Test [1] BaseExperiment, [2] SLAP2Experiment, or [3] Both? (1/2/3): ").strip()
    
    if choice in ['1', '3']:
        test_base_experiment()
    
    if choice in ['2', '3']:
        test_slap2_experiment()
    
    print("\nTest completed!")