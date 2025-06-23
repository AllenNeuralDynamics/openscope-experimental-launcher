"""
Unit tests for the stimulus table utilities.
"""

import pytest
from openscope_experimental_launcher.utils import stimulus_table


class TestStimulusTableFunctions:
    """Test cases for stimulus table functions."""

    def test_placeholder_functions_not_implemented(self):
        """Test that placeholder functions raise NotImplementedError."""
        
        with pytest.raises(NotImplementedError, match="Standardized stimulus table creation not yet implemented"):
            stimulus_table.create_standardized_stimulus_table()
        
        with pytest.raises(NotImplementedError, match="Stimulus table validation not yet implemented"):
            stimulus_table.validate_stimulus_table_schema()
        
        with pytest.raises(NotImplementedError, match="AIND format conversion not yet implemented"):
            stimulus_table.convert_to_aind_format()

    def test_module_docstring_present(self):
        """Test that the module has appropriate documentation."""
        assert stimulus_table.__doc__ is not None
        assert "Stimulus Table Utilities" in stimulus_table.__doc__
        assert "post_processing" in stimulus_table.__doc__
