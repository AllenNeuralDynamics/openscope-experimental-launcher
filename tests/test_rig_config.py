"""
Tests for the rig_config utility module.
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch
import toml

from openscope_experimental_launcher.utils.rig_config import (
    get_rig_config,
    get_config_path,
    load_config,
    create_default_config,
    get_config
)


class TestRigConfig:
    """Test cases for rig configuration utilities."""

    def test_get_config_path_default(self):
        """Test default config path generation."""
        path = get_config_path()
        assert isinstance(path, Path)
        assert path.name == "rig_config.toml"

    def test_get_config_path_custom(self):
        """Test custom config path."""
        custom_path = "/custom/path/config.toml" 
        path = get_config_path(custom_path)
        # Path normalization will change forward slashes to backslashes on Windows
        assert path.name == "config.toml"
        assert "custom" in str(path)
        assert "path" in str(path)

    def test_create_default_config(self):
        """Test creation of default config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.toml"
            create_default_config(config_path)
            
            assert config_path.exists()
            config = toml.load(config_path)
            assert "rig_id" in config

    def test_load_config_default(self):
        """Test loading default config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.toml" 
            create_default_config(config_path)
            
            config = load_config(str(config_path))
            assert isinstance(config, dict)
            assert "rig_id" in config

    def test_load_config_missing_file_create(self):
        """Test loading config with missing file - should create default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "missing_config.toml"
            
            config = load_config(str(config_path), create_if_missing=True)
            assert isinstance(config, dict)
            assert config_path.exists()

    def test_load_config_missing_file_no_create(self):
        """Test loading config with missing file - should not create."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "missing_config.toml"
            
            config = load_config(str(config_path), create_if_missing=False)
            # API actually returns default config even when create_if_missing=False
            assert isinstance(config, dict)
            assert not config_path.exists()

    def test_get_config_existing_key(self):
        """Test getting existing config value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.toml"
            create_default_config(config_path)
            
            value = get_config("rig_id", str(config_path))
            assert isinstance(value, str)

    def test_get_config_missing_key_with_default(self):
        """Test getting missing config value with default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.toml"
            create_default_config(config_path)
            
            value = get_config("nonexistent_key", str(config_path), default="test_default")
            assert value == "test_default"

    def test_get_config_missing_key_no_default(self):
        """Test getting missing config value without default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.toml"
            create_default_config(config_path)
            
            with pytest.raises(KeyError):
                get_config("nonexistent_key", str(config_path))

    def test_get_rig_config_default(self):
        """Test getting full rig config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.toml"
            create_default_config(config_path)
            
            config = get_rig_config(str(config_path))
            assert isinstance(config, dict)
            assert "rig_id" in config

    def test_get_rig_config_integration(self):
        """Test integration with environment variables and defaults."""
        # This is more of an integration test to ensure the function works
        config = get_rig_config()
        assert isinstance(config, dict)
        # Should have at least basic keys after loading/creating config
        assert len(config) > 0

    def test_toml_file_format(self):
        """Test that config file is valid TOML format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.toml"
            create_default_config(config_path)
            
            # Should be able to parse as TOML without error
            config = toml.load(config_path)
            assert isinstance(config, dict)
            
            # Should have expected structure
            assert "rig_id" in config
            assert "output_root_folder" in config