"""
Tests for session builder module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any
import datetime

from src.openscope_experimental_launcher.utils import session_builder


class TestSessionBuilder:
    """Test cases for session builder functions."""

    def test_is_schema_available_true(self):
        """Test schema availability check when schema is available."""
        result = session_builder.is_schema_available()
        assert result is True  # Should be True with aind-data-schema installed

    def test_is_schema_available_false(self):
        """Test schema availability check when schema is not available."""
        with patch('src.openscope_experimental_launcher.utils.session_builder.AIND_SCHEMA_AVAILABLE', False):
            result = session_builder.is_schema_available()
            assert result is False

    def test_build_session_basic(self):
        """Test basic session building with valid parameters."""
        import datetime
        
        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(minutes=30)
        
        params = {
            'stimulus_parameters': {'param1': 'value1'},
            'session_type': 'test_session'
        }
        
        with patch('src.openscope_experimental_launcher.utils.session_builder.Session') as mock_session_class, \
             patch('src.openscope_experimental_launcher.utils.session_builder.StimulusEpoch') as mock_epoch_class, \
             patch('src.openscope_experimental_launcher.utils.session_builder.Software') as mock_software_class:
            
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_epoch_class.return_value = Mock()
            mock_software_class.return_value = Mock()
            
            session = session_builder.build_session(
                start_time=start_time,
                end_time=end_time,
                params=params,
                subject_id='test_subject',
                user_id='test_user',
                session_uuid='test_uuid',
                rig_name='test_rig'
            )
            
            assert session == mock_session

    def test_build_session_with_software(self):
        """Test session building with software parameters."""
        import datetime
        
        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(minutes=30)
        
        params = {
            'stimulus_parameters': {'param1': 'value1'},
            'session_type': 'test_session',
            'script_version': '1.0.0'
        }
        
        with patch('src.openscope_experimental_launcher.utils.session_builder.Session') as mock_session_class, \
             patch('src.openscope_experimental_launcher.utils.session_builder.StimulusEpoch') as mock_epoch_class, \
             patch('src.openscope_experimental_launcher.utils.session_builder.Software') as mock_software_class:
            
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_epoch_class.return_value = Mock()
            mock_software_class.return_value = Mock()
            
            session = session_builder.build_session(
                start_time=start_time,
                end_time=end_time,
                params=params,
                subject_id='test_subject',
                user_id='test_user',
                session_uuid='test_uuid',
                rig_name='test_rig'
            )
            
            assert session == mock_session

    def test_build_session_schema_not_available(self):
        """Test session building when schema is not available."""
        with patch('src.openscope_experimental_launcher.utils.session_builder.AIND_SCHEMA_AVAILABLE', False):
            result = session_builder.build_session()
            assert result is None

    def test_create_script_software_success(self):
        """Test successful script software creation."""
        params = {
            'script_version': '1.0.0',
            'repository_url': 'https://test.git',
            'script_path': 'test_script.py'
        }
        
        with patch('src.openscope_experimental_launcher.utils.session_builder.Software') as mock_software_class:
            mock_software = Mock()
            mock_software_class.return_value = mock_software
            
            # Use correct function signature: params, subject_id, user_id, session_uuid, rig_name
            software = session_builder.create_script_software(
                params, 'test_subject', 'test_user', 'test_session_uuid', 'test_rig'
            )
            
            assert software == mock_software

    def test_create_default_stimulus_epoch_success(self):
        """Test successful default stimulus epoch creation."""
        import datetime
        
        params = {
            'stimulus_parameters': {'param1': 'value1'}
        }
        
        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(minutes=30)
        
        mock_bonsai_software = Mock()
        mock_script_software = Mock()
        
        with patch('src.openscope_experimental_launcher.utils.session_builder.StimulusEpoch') as mock_epoch_class:
            mock_epoch = Mock()
            mock_epoch_class.return_value = mock_epoch
            
            # Use correct function signature: start_time, end_time, params, bonsai_software, script_software, rig_name
            epoch = session_builder.create_default_stimulus_epoch(
                start_time, end_time, params, mock_bonsai_software, mock_script_software, 'test_rig'
            )
            
            assert epoch == mock_epoch

    def test_create_default_data_streams_success(self):
        """Test successful default data streams creation."""
        params = {}
        
        streams = session_builder.create_default_data_streams(params, 'test_rig')
        
        assert isinstance(streams, list)
        assert streams == []  # Default implementation returns empty list

    def test_get_session_type_success(self):
        """Test session type retrieval."""
        params = {'session_type': 'custom_session'}
        
        session_type = session_builder.get_session_type(params, 'test_rig')
        
        assert session_type == 'custom_session'

    def test_get_session_type_default(self):
        """Test session type retrieval with default value."""
        params = {}
        
        session_type = session_builder.get_session_type(params, 'test_rig')
        
        assert session_type == 'test_rig'

    def test_get_rig_id_success(self):
        """Test rig ID retrieval."""
        params = {'rig_id': 'custom_rig_123'}
        
        rig_id = session_builder.get_rig_id(params, 'test_rig')
        
        assert rig_id == 'custom_rig_123'

    def test_get_rig_id_default(self):
        """Test rig ID retrieval with default value."""
        params = {}
        
        rig_id = session_builder.get_rig_id(params, 'test_rig')
        
        assert rig_id == 'test_rig_rig'

    def test_get_mouse_platform_name_from_params(self):
        """Test mouse platform name retrieval from parameters."""
        params = {'mouse_platform': 'test_platform'}
        
        platform_name = session_builder.get_mouse_platform_name(params)
        
        assert platform_name == 'test_platform'

    def test_get_mouse_platform_name_default(self):
        """Test mouse platform name retrieval with default value."""
        params = {}
        
        platform_name = session_builder.get_mouse_platform_name(params)
        
        assert platform_name == 'Fixed platform'

    def test_get_active_mouse_platform_success(self):
        """Test active mouse platform retrieval."""
        params = {'active_mouse_platform': True}
        
        active = session_builder.get_active_mouse_platform(params)
        
        assert active is True

    def test_get_active_mouse_platform_default(self):
        """Test active mouse platform retrieval with default value."""
        params = {}
        
        active = session_builder.get_active_mouse_platform(params)
        
        assert active is False

    def test_get_script_name_success(self):
        """Test script name retrieval."""
        script_name = session_builder.get_script_name('test_rig')
        
        assert isinstance(script_name, str)
        assert len(script_name) > 0

    def test_get_additional_script_parameters_success(self):
        """Test additional script parameters retrieval."""
        params = {'extra_param': 'extra_value'}
        
        extra_params = session_builder.get_additional_script_parameters(params, 'test_rig')
        
        assert isinstance(extra_params, dict)

    def test_create_session_notes_success(self):
        """Test session notes creation."""
        params = {'notes': 'Test notes'}
        
        notes = session_builder.create_session_notes(params, 'test_subject', 'test_user', 'test_rig')
        
        assert isinstance(notes, str)
        assert len(notes) > 0
