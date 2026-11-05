"""Tests for Bonsai version detection and recording (launcher issue #3)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from openscope_experimental_launcher.interfaces import bonsai_interface


def test_config_version_parsed(tmp_path):
    exe = tmp_path / "Bonsai.exe"  # does not exist: forces the config fallback
    config = tmp_path / "Bonsai.config"
    config.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<PackageConfiguration xmlns="urn:bonsai:packageconfiguration">
  <Packages>
    <Package id="Bonsai.Core" version="2.8.5" />
    <Package id="Bonsai" version="2.8.1" />
  </Packages>
</PackageConfiguration>
""",
        encoding="utf-8",
    )
    assert bonsai_interface.get_bonsai_version(str(exe)) == "2.8.1"


def test_config_without_bonsai_package_returns_none(tmp_path):
    (tmp_path / "Bonsai.config").write_text(
        "<PackageConfiguration><Packages>"
        '<Package id="Bonsai.Design" version="9.9.9" />'
        "</Packages></PackageConfiguration>",
        encoding="utf-8",
    )
    assert bonsai_interface.get_bonsai_version(str(tmp_path / "Bonsai.exe")) is None


def test_malformed_config_returns_none(tmp_path):
    (tmp_path / "Bonsai.config").write_text("<not xml", encoding="utf-8")
    assert bonsai_interface.get_bonsai_version(str(tmp_path / "Bonsai.exe")) is None


def test_missing_everything_returns_none(tmp_path):
    assert bonsai_interface.get_bonsai_version(str(tmp_path / "Bonsai.exe")) is None
    assert bonsai_interface.get_bonsai_version("") is None
    assert bonsai_interface.get_bonsai_version(None) is None


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="PE version resources are Windows-only")
def test_exe_product_version_read_from_real_binary():
    """The primary path reads the version resource of the actual executable
    (verified against this machine's python.exe, which always has one)."""
    version = bonsai_interface._read_exe_product_version(sys.executable)
    assert version, "expected a version from a real versioned executable"
    parts = version.split(".")
    assert len(parts) >= 2 and all(p.isdigit() for p in parts)
    # python.exe's product version starts with the interpreter version.
    assert parts[0] == str(sys.version_info.major)
    assert parts[1] == str(sys.version_info.minor)


def test_exe_version_preferred_over_config(tmp_path, monkeypatch):
    """When both sources exist, the binary's version (what actually runs) wins."""
    (tmp_path / "Bonsai.config").write_text(
        '<PackageConfiguration><Packages><Package id="Bonsai" version="1.0.0" />'
        "</Packages></PackageConfiguration>",
        encoding="utf-8",
    )
    exe = tmp_path / "Bonsai.exe"
    exe.write_bytes(b"not a real exe")
    monkeypatch.setattr(
        bonsai_interface, "_read_exe_product_version", lambda path: "2.9.2"
    )
    assert bonsai_interface.get_bonsai_version(str(exe)) == "2.9.2"


def test_launcher_records_version_and_refreshes_processed_params(tmp_path, monkeypatch):
    """_record_bonsai_version adds the version to params and refreshes the
    already-written processed_parameters.json (which save_launcher_metadata
    wrote BEFORE Bonsai setup could have installed the executable)."""
    from openscope_experimental_launcher.launchers.bonsai_launcher import BonsaiLauncher

    launcher = BonsaiLauncher.__new__(BonsaiLauncher)  # skip heavy __init__
    launcher.params = {"subject_id": "s1"}
    launcher.output_session_folder = str(tmp_path)

    meta_dir = tmp_path / "launcher_metadata"
    meta_dir.mkdir()
    processed = meta_dir / "processed_parameters.json"
    processed.write_text(json.dumps({"subject_id": "s1"}), encoding="utf-8")

    monkeypatch.setattr(bonsai_interface, "get_bonsai_version", lambda path: "2.8.1")
    launcher._record_bonsai_version(r"C:\fake\Bonsai.exe")

    assert launcher.params["bonsai_version"] == "2.8.1"
    on_disk = json.loads(processed.read_text(encoding="utf-8"))
    assert on_disk["bonsai_version"] == "2.8.1"
    assert on_disk["subject_id"] == "s1"


def test_launcher_recording_is_noop_without_version(tmp_path, monkeypatch):
    from openscope_experimental_launcher.launchers.bonsai_launcher import BonsaiLauncher

    launcher = BonsaiLauncher.__new__(BonsaiLauncher)
    launcher.params = {"subject_id": "s1"}
    launcher.output_session_folder = str(tmp_path)

    monkeypatch.setattr(bonsai_interface, "get_bonsai_version", lambda path: None)
    launcher._record_bonsai_version(r"C:\fake\Bonsai.exe")  # must not raise

    assert "bonsai_version" not in launcher.params
