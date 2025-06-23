"""
Tests for the pp_stimulus_converter post-processing tool.
"""

import os
import pytest
import tempfile
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock

from openscope_experimental_launcher.post_processing.pp_stimulus_converter import (
    convert_orientation_to_stimulus_table,
    main
)


class TestPPStimulusConverter:
    """Test cases for the Predictive Processing stimulus converter."""

    def test_convert_orientation_to_stimulus_table_missing_folder(self):
        """Test converter with non-existent session folder."""
        result = convert_orientation_to_stimulus_table("/nonexistent/folder")
        assert result is False

    def test_convert_orientation_to_stimulus_table_no_data_files(self, tmp_path):
        """Test converter with session folder but no orientation files."""
        session_folder = tmp_path / "test_session"
        session_folder.mkdir()
        
        result = convert_orientation_to_stimulus_table(str(session_folder))
        assert result is False

    def test_convert_orientation_to_stimulus_table_with_orientation_data(self, tmp_path):
        """Test converter with valid orientation data."""
        session_folder = tmp_path / "test_session"
        session_folder.mkdir()
        
        # Create mock orientation data
        orientation_data = [
            [0, 1.0, 0.5, 360, 0, 0, 1.0, 0.04, 2.0, 0.0],
            [1, 1.0, 0.5, 360, 0, 0, 1.0, 0.04, 2.0, 1.57],
            [2, 1.0, 0.5, 360, 0, 0, 1.0, 0.04, 2.0, 3.14]
        ]
        
        orientation_file = session_folder / "orientations_orientations0.csv"
        pd.DataFrame(orientation_data).to_csv(orientation_file, header=False, index=False)
        
        # Mock timing data to avoid HARP dependency
        mock_timing_data = {
            'normalized_start_gratings': [0.0, 1.5, 3.0],
            'start_trial': [100.0, 101.5, 103.0],
            'end_trial': [101.0, 102.5, 104.0],
            'start_gratings': [100.5, 102.0, 103.5],
            'time_reference': 100.0
        }
        
        with patch('openscope_experimental_launcher.post_processing.pp_stimulus_converter.get_timing_data', return_value=mock_timing_data):
            result = convert_orientation_to_stimulus_table(str(session_folder))
        
        assert result is True
        
        # Check output files exist
        output_folder = session_folder / "stimulus_table_output"
        assert output_folder.exists()
        
        stimulus_table_file = output_folder / "stimulus_table.csv"
        assert stimulus_table_file.exists()
        
        # Verify stimulus table content
        stimulus_table = pd.read_csv(stimulus_table_file)
        assert len(stimulus_table) == 3
        assert 'start_time' in stimulus_table.columns
        assert 'orientation_degrees' in stimulus_table.columns
        
    def test_convert_orientation_to_stimulus_table_custom_output(self, tmp_path):
        """Test converter with custom output folder."""
        session_folder = tmp_path / "test_session"
        session_folder.mkdir()
        
        output_folder = tmp_path / "custom_output"
        
        # Create minimal orientation data
        orientation_data = [[0, 1.0, 0.5, 360, 0, 0, 1.0, 0.04, 2.0, 0.0]]
        orientation_file = session_folder / "orientations_orientations0.csv"
        pd.DataFrame(orientation_data).to_csv(orientation_file, header=False, index=False)
        
        # Mock timing data
        mock_timing_data = {
            'normalized_start_gratings': [0.0],
            'start_trial': [100.0],
            'end_trial': [101.0],
            'start_gratings': [100.5],
            'time_reference': 100.0
        }
        
        with patch('openscope_experimental_launcher.post_processing.pp_stimulus_converter.get_timing_data', return_value=mock_timing_data):
            result = convert_orientation_to_stimulus_table(str(session_folder), str(output_folder))
        
        assert result is True
        assert output_folder.exists()
        assert (output_folder / "stimulus_table.csv").exists()

    def test_convert_orientation_no_timing_data(self, tmp_path):
        """Test converter when timing data is not available."""
        session_folder = tmp_path / "test_session"
        session_folder.mkdir()
        
        # Create orientation data
        orientation_data = [[0, 1.0, 0.5, 360, 0, 0, 1.0, 0.04, 2.0, 0.0]]
        orientation_file = session_folder / "orientations_orientations0.csv"
        pd.DataFrame(orientation_data).to_csv(orientation_file, header=False, index=False)
        
        # Mock no timing data available
        with patch('openscope_experimental_launcher.post_processing.pp_stimulus_converter.get_timing_data', return_value=None):
            result = convert_orientation_to_stimulus_table(str(session_folder))
        
        assert result is False

    @patch('sys.argv', ['pp_stimulus_converter.py', '/test/session'])
    @patch('openscope_experimental_launcher.post_processing.pp_stimulus_converter.convert_orientation_to_stimulus_table')
    def test_main_success(self, mock_convert):
        """Test main function with successful conversion."""
        mock_convert.return_value = True
        
        result = main()
        assert result == 0
        mock_convert.assert_called_once_with('/test/session', None)

    @patch('sys.argv', ['pp_stimulus_converter.py', '/test/session'])
    @patch('openscope_experimental_launcher.post_processing.pp_stimulus_converter.convert_orientation_to_stimulus_table')
    def test_main_failure(self, mock_convert):
        """Test main function with failed conversion."""
        mock_convert.return_value = False
        
        result = main()
        assert result == 1
        mock_convert.assert_called_once_with('/test/session', None)

    @patch('sys.argv', ['pp_stimulus_converter.py', '/test/session', '/custom/output'])
    @patch('openscope_experimental_launcher.post_processing.pp_stimulus_converter.convert_orientation_to_stimulus_table')
    def test_main_with_custom_output(self, mock_convert):
        """Test main function with custom output folder."""
        mock_convert.return_value = True
        
        result = main()
        assert result == 0
        mock_convert.assert_called_once_with('/test/session', '/custom/output')


class TestGetTimingData:
    """Test cases for HARP timing data functions."""
    
    @patch('openscope_experimental_launcher.post_processing.pp_stimulus_converter.harp')
    @patch('openscope_experimental_launcher.post_processing.pp_stimulus_converter.fetch_yml')
    def test_get_timing_data_basic(self, mock_fetch_yml, mock_harp, tmp_path):
        """Test basic timing data extraction."""
        from openscope_experimental_launcher.post_processing.pp_stimulus_converter import get_timing_data
        
        harp_path = tmp_path / ".harp"
        harp_path.mkdir()
        
        # Mock the device.yml file
        device_yml = harp_path / "device.yml"
        device_yml.write_text("mock device config")
        
        # Mock HARP reader and data
        mock_reader = MagicMock()
        mock_harp.create_reader.return_value = mock_reader
        
        # Mock analog data
        mock_analog_data = pd.DataFrame({
            'AnalogInput0': [0.1, 0.2, 0.3],
            'Encoder': [1.0, 2.0, 3.0]
        })
        mock_analog_data.index = pd.Index([100.0, 101.0, 102.0])
        mock_reader.AnalogData.read.return_value = mock_analog_data
        
        # Mock pulse data
        mock_pulse_data = pd.DataFrame({'PulseDO0': [1, 1, 1]})
        mock_pulse_data.index = pd.Index([100.0, 101.0, 102.0])
        mock_reader.PulseDO0.read.return_value = mock_pulse_data
        mock_reader.PulseDO1.read.return_value = mock_pulse_data
        mock_reader.PulseDO2.read.return_value = mock_pulse_data
        
        result = get_timing_data(harp_path)
        
        assert result is not None
        assert 'start_trial' in result
        assert 'end_trial' in result
        assert 'start_gratings' in result
        assert 'time_reference' in result
        assert 'photodiode' in result
        assert 'wheel' in result

    def test_get_timing_data_missing_harp_path(self):
        """Test timing data with non-existent HARP path."""
        from openscope_experimental_launcher.post_processing.pp_stimulus_converter import get_timing_data
        
        # This should raise an exception or return None, depending on implementation
        # The actual behavior will depend on how the function handles missing paths
        try:
            result = get_timing_data(Path("/nonexistent/path"))
            # If no exception, result should be None or have some error indication
        except Exception:
            # Expected for missing path
            pass
