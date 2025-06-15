"""
Tests for the refactored SLAP2 session builder.
"""

import pytest
import datetime
from unittest.mock import Mock, patch

from openscope_experimental_launcher.slap2.session_builder import SLAP2SessionBuilder


class TestSLAP2SessionBuilderRefactored:
    """Test cases for the refactored SLAP2SessionBuilder."""
    
    def test_initialization(self):
        """Test that SLAP2SessionBuilder initializes correctly."""
        builder = SLAP2SessionBuilder()
        assert builder.rig_name == "SLAP2"
    
    @patch('openscope_experimental_launcher.slap2.session_builder.AIND_SCHEMA_AVAILABLE', False)
    def test_build_session_without_schema(self):
        """Test that build_session returns None when schema is not available."""
        builder = SLAP2SessionBuilder()
        result = builder.build_session()
        assert result is None
    
    @patch('openscope_experimental_launcher.slap2.session_builder.AIND_SCHEMA_AVAILABLE', True)
    def test_build_session_backward_compatibility(self):
        """Test that the SLAP2-specific build_session interface still works."""
        builder = SLAP2SessionBuilder()
        
        # Mock the Session class and its dependencies
        with patch('openscope_experimental_launcher.slap2.session_builder.Session') as mock_session:
            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            
            # Test the SLAP2-specific interface with slap_fovs parameter
            result = builder.build_session(
                start_time=datetime.datetime.now(),
                end_time=datetime.datetime.now(),
                params={"num_trials": 100},
                mouse_id="test_mouse",
                user_id="test_user",
                experimenter_name="Test Experimenter",
                session_uuid="test-uuid-123",
                slap_fovs=[]  # SLAP2-specific parameter
            )
            
            # Verify Session was called
            mock_session.assert_called_once()
            call_args = mock_session.call_args[1]  # keyword arguments
            
            assert call_args['subject_id'] == "test_mouse"
            assert call_args['session_type'] == "SLAP2"
            assert call_args['rig_id'] == "slap2_rig"
            assert result == mock_session_instance
    
    def test_rig_specific_methods(self):
        """Test SLAP2-specific helper methods."""
        builder = SLAP2SessionBuilder()
        params = {
            "laser_wavelength": 920,
            "laser_power": 15.0,
            "laser_name": "Custom SLAP2 Laser",
            "detector_name": "Custom Detector",
            "exposure_time": 2.0
        }
        
        # Test light source creation
        light_sources = builder._create_light_sources(params)
        assert len(light_sources) == 1
        # Note: In real test, you'd check the laser_config properties,
        # but we're avoiding deep mocking of aind-data-schema objects
        
        # Test detector creation
        detectors = builder._create_detectors(params)
        assert len(detectors) == 1
    
    def test_empty_light_sources_and_detectors(self):
        """Test that empty configurations are handled correctly."""
        builder = SLAP2SessionBuilder()
        params = {}
        
        light_sources = builder._create_light_sources(params)
        assert len(light_sources) == 0
        
        detectors = builder._create_detectors(params)
        assert len(detectors) == 0
