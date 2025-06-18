"""
Tests for the base session builder functionality.
"""

import pytest
import datetime
from unittest.mock import Mock, patch

from openscope_experimental_launcher.base.session_builder import BaseSessionBuilder


class TestableSessionBuilder(BaseSessionBuilder):
    """Test implementation of BaseSessionBuilder for testing purposes."""
    
    def __init__(self):
        super().__init__("TestRig")
    
    def _create_stimulus_epoch(self, start_time, end_time, params, bonsai_software, script_software, **kwargs):
        # Import here to avoid import issues in tests
        try:
            from aind_data_schema.core.session import StimulusEpoch, StimulusModality
            return StimulusEpoch(
                stimulus_start_time=start_time,
                stimulus_end_time=end_time,
                stimulus_name="Test Stimulus",
                stimulus_modalities=[StimulusModality.VISUAL],
                software=[bonsai_software],
                script=script_software,
                trials_total=10,
                trials_finished=10,
                notes="Test stimulus epoch"
            )
        except ImportError:
            return Mock()
    
    def _create_data_streams(self, params, **kwargs):
        return []


class TestBaseSessionBuilder:
    """Test cases for BaseSessionBuilder."""
    
    def test_initialization(self):
        """Test that BaseSessionBuilder initializes correctly."""
        builder = TestableSessionBuilder()
        assert builder.rig_name == "TestRig"
    
    @patch('openscope_experimental_launcher.base.session_builder.AIND_SCHEMA_AVAILABLE', False)
    def test_build_session_without_schema(self):
        """Test that build_session returns None when schema is not available."""
        builder = TestableSessionBuilder()
        result = builder.build_session()
        assert result is None
    
    @patch('openscope_experimental_launcher.base.session_builder.AIND_SCHEMA_AVAILABLE', True)
    def test_build_session_with_minimal_params(self):
        """Test building session with minimal parameters."""
        builder = TestableSessionBuilder()
        
        # Mock the Session class and its dependencies
        with patch('openscope_experimental_launcher.base.session_builder.Session') as mock_session:
            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            
            result = builder.build_session(
                subject_id="test_mouse",
                user_id="test_user",
                session_uuid="test-uuid-123"
            )
            
            # Verify Session was called with expected parameters
            mock_session.assert_called_once()
            call_args = mock_session.call_args[1]  # keyword arguments
            
            assert call_args['subject_id'] == "test_mouse"
            assert call_args['session_type'] == "TestRig"
            assert call_args['rig_id'] == "testrig_rig"
            assert "test_user" in call_args['experimenter_full_name']
            
            assert result == mock_session_instance
    
    def test_helper_methods(self):
        """Test the helper methods for configuration."""
        builder = TestableSessionBuilder()
        params = {
            "session_type": "Custom",
            "rig_id": "custom_rig",
            "mouse_platform": "Treadmill",
            "active_mouse_platform": True,
            "session_notes": "Custom experiment"
        }
        
        assert builder._get_session_type(params) == "Custom"
        assert builder._get_rig_id(params) == "custom_rig"
        assert builder._get_mouse_platform_name(params) == "Treadmill"
        assert builder._get_active_mouse_platform(params) is True
        
        notes = builder._create_session_notes(params, "mouse123", "user456")
        assert "TestRig experiment session for mouse123 by user456" in notes
        assert "Custom experiment" in notes
    
    def test_default_values(self):
        """Test that default values are used when parameters are not provided."""
        builder = TestableSessionBuilder()
        params = {}
        
        assert builder._get_session_type(params) == "TestRig"
        assert builder._get_rig_id(params) == "testrig_rig"
        assert builder._get_mouse_platform_name(params) == "Fixed platform"
        assert builder._get_active_mouse_platform(params) is False
        
        notes = builder._create_session_notes(params, "mouse123", "")
        assert notes == "TestRig experiment session for mouse123"
