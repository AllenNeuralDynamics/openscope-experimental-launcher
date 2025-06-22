"""
Simple test for package imports and basic functionality.
"""

import pytest


def test_package_imports():
    """Test that all main package components can be imported."""
    try:
        from openscope_experimental_launcher import BaseLauncher, BonsaiLauncher, SLAP2Launcher
        from openscope_experimental_launcher.utils import git_manager, process_monitor
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import package components: {e}")


def test_base_launcher_creation():
    """Test that BaseLauncher can be instantiated."""
    from openscope_experimental_launcher import BaseLauncher

    launcher = BaseLauncher()
    assert launcher is not None
    assert hasattr(launcher, 'platform_info')
    assert hasattr(launcher, 'session_uuid')


def test_slap2_launcher_creation():
    """Test that SLAP2Launcher can be instantiated."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
    
    from slap2_launcher import SLAP2Launcher
    launcher = SLAP2Launcher()
    assert launcher is not None
    assert launcher.session_type == "SLAP2"


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
    test_base_launcher_creation()
    test_slap2_launcher_creation()
    print("✓ All basic tests passed!")
