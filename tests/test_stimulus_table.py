"""
Unit tests for the functional stimulus table utilities.
"""

import os
import pytest
import pandas as pd
from unittest.mock import patch
from openscope_experimental_launcher.utils import stimulus_table


class TestStimulusTableFunctions:
    """Test cases for stimulus table functions."""

    def test_generate_slap2_stimulus_table_mock_fallback(self):
        """Test stimulus table generation falls back to mock when no Bonsai output."""
        params = {"num_trials": 5}
        session_output_path = "/nonexistent/path/output.pkl"
        
        with patch('openscope_experimental_launcher.utils.stimulus_table._load_bonsai_output', return_value=None):
            result = stimulus_table.generate_slap2_stimulus_table(params, session_output_path)
            
        assert result is not None
        assert len(result) == 5
        assert 'trial_index' in result.columns
        assert 'stimulus_type' in result.columns

    def test_save_stimulus_table_success(self, tmp_path):
        """Test successful stimulus table saving."""
        df = pd.DataFrame({'trial_index': [0, 1], 'stimulus_type': ['a', 'b']})
        output_path = tmp_path / "test_table.csv"
        
        result = stimulus_table.save_stimulus_table(df, str(output_path))
        
        assert result is True
        assert output_path.exists()

    def test_get_trial_statistics_basic(self):
        """Test basic trial statistics calculation."""
        df = pd.DataFrame({
            'trial_index': [0, 1, 2],
            'stimulus_type': ['standard', 'oddball', 'standard'],
            'success': [True, False, True]
        })
        
        stats = stimulus_table.get_trial_statistics(df)
        
        assert stats['total_trials'] == 3
        assert stats['successful_trials'] == 2
        assert stats['trial_types']['standard'] == 2
        assert stats['trial_types']['oddball'] == 1
