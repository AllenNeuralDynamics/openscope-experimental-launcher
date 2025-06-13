"""
Simple test for package imports and basic functionality.
"""

import pytest


def test_package_imports():
    """Test that all main package components can be imported."""
    try:
        from openscope_experimental_launcher import BaseExperiment, SLAP2Experiment
        from openscope_experimental_launcher.utils import GitManager, ConfigLoader, ProcessMonitor
        from openscope_experimental_launcher.slap2 import SLAP2SessionBuilder, SLAP2StimulusTableGenerator
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import package components: {e}")


def test_base_experiment_creation():
    """Test that BaseExperiment can be instantiated."""
    from openscope_experimental_launcher import BaseExperiment

    experiment = BaseExperiment()
    assert experiment is not None
    assert hasattr(experiment, 'platform_info')
    assert hasattr(experiment, 'session_uuid')


def test_slap2_experiment_creation():
    """Test that SLAP2Experiment can be instantiated."""
    from openscope_experimental_launcher import SLAP2Experiment

    experiment = SLAP2Experiment()
    assert experiment is not None
    assert experiment.session_type == "SLAP2"
    assert hasattr(experiment, 'slap_fovs')


@pytest.mark.unit
def test_version_availability():
    """Test that package version is available."""
    try:
        from openscope_experimental_launcher import __version__
        assert __version__ is not None
    except ImportError:
        # Version might not be set in development
        pytest.skip("Version not available in development mode")


if __name__ == "__main__":
    # Run basic tests if executed directly
    test_package_imports()
    test_base_experiment_creation()
    test_slap2_experiment_creation()
    print("✓ All basic tests passed!")
