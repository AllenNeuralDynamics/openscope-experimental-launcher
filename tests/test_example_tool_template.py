"""
Tests for the example tool template.
"""

import pytest
from unittest.mock import patch

from openscope_experimental_launcher.post_processing.example_tool_template import (
    process_session,
    main
)


class TestExampleToolTemplate:
    """Test cases for the example tool template."""

    def test_process_session_missing_folder(self):
        """Test that process_session handles missing session folder."""
        result = process_session("/test/session")
        assert result is False

    def test_process_session_missing_folder_with_output(self):
        """Test that process_session handles missing session folder with output folder."""
        result = process_session("/test/session", "/test/output")
        assert result is False

    @patch('sys.argv', ['example_tool_template.py', '/test/session'])
    @patch('openscope_experimental_launcher.post_processing.example_tool_template.process_session')    def test_main_basic(self, mock_process):
        """Test main function with basic arguments."""
        mock_process.return_value = False  # Simulate failure
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    @patch('sys.argv', ['example_tool_template.py', '/test/session', '/test/output'])
    @patch('openscope_experimental_launcher.post_processing.example_tool_template.process_session')
    def test_main_with_output(self, mock_process):
        """Test main function with output folder."""
        mock_process.return_value = False  # Simulate failure
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    @patch('sys.argv', ['example_tool_template.py', '/test/session'])
    @patch('openscope_experimental_launcher.post_processing.example_tool_template.process_session')
    def test_main_success_hypothetical(self, mock_process):
        """Test main function with successful processing."""
        mock_process.return_value = True
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        mock_process.assert_called_once_with('/test/session', None)
