"""
Unit tests for the SLAP2StimulusTableGenerator class.
"""

import os
import pytest
import pandas as pd
from unittest.mock import Mock, patch, mock_open
from openscope_experimental_launcher.slap2.stimulus_table import SLAP2StimulusTableGenerator


class TestSLAP2StimulusTableGenerator:
    """Test cases for SLAP2StimulusTableGenerator class."""

    def test_init(self):
        """Test SLAP2StimulusTableGenerator initialization."""
        generator = SLAP2StimulusTableGenerator()
        assert generator is not None

    def test_generate_stimulus_table_with_bonsai_output(self, temp_dir):
        """Test stimulus table generation from Bonsai output."""
        generator = SLAP2StimulusTableGenerator()
        params = {"session_uuid": "test-uuid"}
        session_output_path = os.path.join(temp_dir, "output.pkl")
        
        # Mock Bonsai output file
        mock_df = pd.DataFrame({
            'trial_index': [0, 1, 2],
            'start_time': [0.0, 2.0, 4.0],
            'stimulus_type': ['standard', 'oddball', 'standard']
        })
        
        with patch.object(generator, '_load_bonsai_output', return_value=mock_df):
            result = generator.generate_stimulus_table(params, session_output_path)
            
            assert result is not None
            assert len(result) == 3

    def test_generate_stimulus_table_mock_fallback(self, temp_dir):
        """Test stimulus table generation falling back to mock data."""
        generator = SLAP2StimulusTableGenerator()
        params = {"num_trials": 10}
        session_output_path = os.path.join(temp_dir, "output.pkl")
        
        with patch.object(generator, '_load_bonsai_output', return_value=None):
            result = generator.generate_stimulus_table(params, session_output_path)
            
            assert result is not None
            assert len(result) == 10
            assert 'trial_index' in result.columns
            assert 'stimulus_type' in result.columns

    def test_load_bonsai_output_file_found(self, temp_dir):
        """Test loading Bonsai output when file exists."""
        generator = SLAP2StimulusTableGenerator()
        session_output_path = os.path.join(temp_dir, "output.pkl")
        params = {"session_uuid": "test-uuid"}
        
        # Create a test CSV file
        test_file = os.path.join(temp_dir, "trials.csv")
        test_df = pd.DataFrame({
            'trial': [0, 1, 2],
            'start': [0.0, 2.0, 4.0],
            'stimulus': ['standard', 'oddball', 'standard']
        })
        test_df.to_csv(test_file, index=False)
        
        with patch('os.path.exists', return_value=True), \
             patch('pandas.read_csv', return_value=test_df), \
             patch.object(generator, '_validate_bonsai_output', return_value=True), \
             patch.object(generator, '_standardize_bonsai_output', return_value=test_df):
            
            result = generator._load_bonsai_output(session_output_path, params)
            
            assert result is not None

    def test_load_bonsai_output_no_file(self, temp_dir):
        """Test loading Bonsai output when no file exists."""
        generator = SLAP2StimulusTableGenerator()
        session_output_path = os.path.join(temp_dir, "output.pkl")
        params = {"session_uuid": "test-uuid"}
        
        with patch('os.path.exists', return_value=False):
            result = generator._load_bonsai_output(session_output_path, params)
            
            assert result is None

    def test_validate_bonsai_output_valid(self):
        """Test validation of valid Bonsai output."""
        generator = SLAP2StimulusTableGenerator()
        df = pd.DataFrame({
            'trial_index': [0, 1, 2],
            'start_time': [0.0, 2.0, 4.0],
            'stimulus_type': ['standard', 'oddball', 'standard']
        })
        
        result = generator._validate_bonsai_output(df)
        assert result is True

    def test_validate_bonsai_output_invalid(self):
        """Test validation of invalid Bonsai output."""
        generator = SLAP2StimulusTableGenerator()
        df = pd.DataFrame({
            'irrelevant_column': [0, 1, 2]
        })
        
        result = generator._validate_bonsai_output(df)
        assert result is False

    def test_standardize_bonsai_output(self):
        """Test standardization of Bonsai output."""
        generator = SLAP2StimulusTableGenerator()
        df = pd.DataFrame({
            'trial': [0, 1, 2],
            'start_time': [0.0, 2.0, 4.0],
            'stimulus': ['standard', 'oddball', 'standard']
        })
        
        result = generator._standardize_bonsai_output(df)
        
        assert 'trial_index' in result.columns
        assert 'start_time' in result.columns  # Keep original column name
        assert 'stimulus_type' in result.columns

    def test_generate_mock_stimulus_table(self):
        """Test mock stimulus table generation."""
        generator = SLAP2StimulusTableGenerator()
        params = {
            "num_trials": 20,
            "trial_duration": 1.0,
            "inter_trial_interval": 0.5,
            "oddball_probability": 0.2,
            "laser_power": 10.0,
            "frame_rate": 30.0
        }
        
        result = generator._generate_mock_stimulus_table(params)
        
        assert len(result) == 20
        assert 'trial_index' in result.columns
        assert 'stimulus_type' in result.columns
        assert 'laser_power' in result.columns
        assert 'frame_rate' in result.columns
        
        # Check that some trials are oddball
        oddball_count = (result['stimulus_type'] == 'oddball').sum()
        assert oddball_count > 0

    def test_save_stimulus_table_success(self, temp_dir):
        """Test successful stimulus table saving."""
        generator = SLAP2StimulusTableGenerator()
        df = pd.DataFrame({
            'trial_index': [0, 1, 2],
            'stimulus_type': ['standard', 'oddball', 'standard']
        })
        output_path = os.path.join(temp_dir, "stimulus_table.csv")
        
        result = generator.save_stimulus_table(df, output_path)
        
        assert result is True
        assert os.path.exists(output_path)

    def test_save_stimulus_table_failure(self, temp_dir):
        """Test stimulus table saving failure."""
        generator = SLAP2StimulusTableGenerator()
        df = pd.DataFrame({'test': [1, 2, 3]})
        # Invalid path
        output_path = "/invalid/path/stimulus_table.csv"
        
        result = generator.save_stimulus_table(df, output_path)
        
        assert result is False

    def test_get_trial_statistics(self):
        """Test trial statistics calculation."""
        generator = SLAP2StimulusTableGenerator()
        df = pd.DataFrame({
            'trial_index': [0, 1, 2, 3, 4],
            'stimulus_start_time': [0.0, 2.0, 4.0, 6.0, 8.0],
            'stimulus_end_time': [1.0, 3.0, 5.0, 7.0, 9.0],
            'stimulus_type': ['standard', 'oddball', 'standard', 'standard', 'oddball'],
            'success': [True, True, False, True, True]
        })
        
        stats = generator.get_trial_statistics(df)
        
        assert stats['total_trials'] == 5
        assert stats['successful_trials'] == 4
        assert stats['trial_types']['standard'] == 3
        assert stats['trial_types']['oddball'] == 2
        assert stats['average_trial_duration'] == 1.0
        # Fix expected duration - last end time is 9.0, first start time is 0.0
        assert stats['total_experiment_duration'] == 9.0

    def test_get_trial_statistics_error(self):
        """Test trial statistics calculation with error."""
        generator = SLAP2StimulusTableGenerator()
        # Invalid DataFrame that will cause an error
        df = None
        
        stats = generator.get_trial_statistics(df)
        
        assert 'error' in stats