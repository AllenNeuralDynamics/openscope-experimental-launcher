"""
Simple tests for post-processing modules to improve coverage.
"""

import pytest
from pathlib import Path


def test_post_processing_imports():
    """Test that post-processing modules can be imported."""
    # Test that modules can be imported without errors
    from openscope_experimental_launcher.post_processing import example_tool_template
    from openscope_experimental_launcher.post_processing import pp_stimulus_converter
    
    assert hasattr(example_tool_template, 'process_session')
    assert hasattr(example_tool_template, 'main')
    assert hasattr(pp_stimulus_converter, 'convert_orientation_to_stimulus_table')


def test_example_tool_template_process_session_missing_folder():
    """Test example tool with missing session folder."""
    from openscope_experimental_launcher.post_processing.example_tool_template import process_session
    
    # This should return False for non-existent path
    result = process_session("/definitely/does/not/exist")
    assert result is False


def test_pp_stimulus_converter_missing_folder():
    """Test PP stimulus converter with missing session folder."""
    from openscope_experimental_launcher.post_processing.pp_stimulus_converter import convert_orientation_to_stimulus_table
    
    # This should return False for non-existent path  
    result = convert_orientation_to_stimulus_table("/definitely/does/not/exist")
    assert result is False


def test_post_processing_modules_have_docstrings():
    """Test that post-processing modules have proper documentation."""
    from openscope_experimental_launcher.post_processing import example_tool_template
    from openscope_experimental_launcher.post_processing import pp_stimulus_converter
    
    assert example_tool_template.__doc__ is not None
    assert pp_stimulus_converter.__doc__ is not None
    assert example_tool_template.process_session.__doc__ is not None
    assert pp_stimulus_converter.convert_orientation_to_stimulus_table.__doc__ is not None
