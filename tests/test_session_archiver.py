import json
import os
from pathlib import Path

import pytest

from openscope_experimental_launcher.post_acquisition import session_archiver


def _default_prompt(prompt, default):
    return default


def test_session_archiver_transfers_and_verifies(tmp_path):
    session_dir = tmp_path / "session"
    network_dir = tmp_path / "network"
    backup_dir = tmp_path / "backup"
    session_dir.mkdir()

    # Create test files including a nested path
    (session_dir / "file1.txt").write_text("hello world", encoding="utf-8")
    nested_dir = session_dir / "nested"
    nested_dir.mkdir()
    (nested_dir / "file2.bin").write_bytes(b"binary-data")

    params = {
        "session_dir": str(session_dir),
        "network_dir": str(network_dir),
        "backup_dir": str(backup_dir),
        "session_uuid": "session-test",
        "include_patterns": ["*.txt", "nested/*"],
        "exclude_patterns": ["*.ignore"],
        "checksum_algo": "sha256",
        "dry_run": False,
        "max_retries": 0,
    }
    param_file = tmp_path / "params.json"
    param_file.write_text(json.dumps(params), encoding="utf-8")

    exit_code = session_archiver.run_post_acquisition(
        str(param_file), overrides={"prompt_func": _default_prompt}
    )
    assert exit_code == 0

    # Files should be copied to the network directory
    assert (network_dir / "file1.txt").read_text(encoding="utf-8") == "hello world"
    assert (network_dir / "nested" / "file2.bin").read_bytes() == b"binary-data"

    # Original files remain in place; backups receive copies
    assert (session_dir / "file1.txt").exists()
    assert (session_dir / "nested" / "file2.bin").exists()
    assert (backup_dir / "file1.txt").exists()
    assert (backup_dir / "nested" / "file2.bin").exists()

    # Manifest should record successful transfers
    manifest_path = session_dir / "launcher_metadata" / "session_archiver_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rel_paths = {"file1.txt", "nested/file2.bin"}
    assert set(manifest["files"].keys()) == rel_paths
    for meta in manifest["files"].values():
        assert meta["status"] == "complete"
        assert Path(meta["network_path"]).exists()
        assert Path(meta["backup_path"]).exists()
        assert meta["checksum"]
        assert meta["network_copy"] is True
        assert meta["backup_copy"] is True


def test_session_archiver_skips_network_when_confirmation_declined(tmp_path):
    session_dir = tmp_path / "session"
    network_dir = tmp_path / "network"
    backup_dir = tmp_path / "backup"
    session_dir.mkdir()

    (session_dir / "file.txt").write_text("payload", encoding="utf-8")

    params = {
        "session_dir": str(session_dir),
        "network_dir": str(network_dir),
        "backup_dir": str(backup_dir),
        "session_uuid": "session-test",
    }
    param_file = tmp_path / "params.json"
    param_file.write_text(json.dumps(params), encoding="utf-8")

    responses = iter(
        [
            str(network_dir),
            str(backup_dir),
            "no",  # disable network transfer
            "yes",  # keep backup transfer enabled
        ]
    )

    def prompt_stub(prompt, default):
        try:
            return next(responses)
        except StopIteration:
            return default

    exit_code = session_archiver.run_post_acquisition(
        str(param_file), overrides={"prompt_func": prompt_stub}
    )
    assert exit_code == 0

    # Network directory should not be created when transfer is declined
    assert not network_dir.exists()

    # Original file remains alongside the backup copy
    assert (session_dir / "file.txt").exists()
    assert (backup_dir / "file.txt").read_text(encoding="utf-8") == "payload"

    manifest_path = session_dir / "launcher_metadata" / "session_archiver_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = manifest["files"]["file.txt"]
    assert entry["status"] == "complete"
    assert entry["network_copy"] is False
    assert entry["backup_copy"] is True
    assert "network_path" not in entry
    assert Path(entry["backup_path"]).exists()


def test_session_archiver_handles_locked_file(tmp_path):
    if os.name != "nt":
        pytest.skip("Windows-specific locking behavior")
    win32file = pytest.importorskip("win32file")
    win32con = pytest.importorskip("win32con")

    session_dir = tmp_path / "session"
    network_dir = tmp_path / "network"
    backup_dir = tmp_path / "backup"
    session_dir.mkdir()

    locked_file = session_dir / "launcher.log"
    locked_file.write_text("log data", encoding="utf-8")
    handle = win32file.CreateFile(
        str(locked_file),
        win32con.GENERIC_READ | win32con.GENERIC_WRITE,
        win32con.FILE_SHARE_READ,
        None,
        win32con.OPEN_EXISTING,
        win32con.FILE_ATTRIBUTE_NORMAL,
        None,
    )

    params = {
        "session_dir": str(session_dir),
        "network_dir": str(network_dir),
        "backup_dir": str(backup_dir),
        "session_uuid": "session-test",
    }
    param_file = tmp_path / "params.json"
    param_file.write_text(json.dumps(params), encoding="utf-8")

    responses = iter(
        [
            str(network_dir),
            str(backup_dir),
            "yes",
            "yes",
        ]
    )

    def prompt_stub(prompt, default):
        try:
            return next(responses)
        except StopIteration:
            return default

    try:
        exit_code = session_archiver.run_post_acquisition(
            str(param_file), overrides={"prompt_func": prompt_stub}
        )
    finally:
        win32file.CloseHandle(handle)

    assert exit_code == 0

    # The network copy should succeed even though the original is locked
    assert (network_dir / "launcher.log").read_text(encoding="utf-8") == "log data"

    # Original file remains in place because it could not be moved
    assert (session_dir / "launcher.log").exists()
    assert (backup_dir / "launcher.log").exists()

    manifest_path = session_dir / "launcher_metadata" / "session_archiver_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = manifest["files"]["launcher.log"]
    assert entry["status"] == "complete"
    assert entry["network_copy"] is True
    assert entry["backup_copy"] is True
    assert "network_path" in entry
    assert "backup_error" not in entry


def test_session_archiver_always_includes_instrument_json_with_routing_manifest(tmp_path):
    session_dir = tmp_path / "session"
    network_dir = tmp_path / "network"
    backup_dir = tmp_path / "backup"
    session_dir.mkdir()

    # Files present in session root.
    (session_dir / "instrument.json").write_text("{\"instrument\": true}\n", encoding="utf-8")
    (session_dir / "file.txt").write_text("payload\n", encoding="utf-8")

    # Routing manifest deliberately omits instrument.json.
    routing_manifest_path = session_dir / "launcher_metadata" / "routing_manifest.json"
    routing_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    routing_manifest_path.write_text(
        json.dumps({"entries": [{"files": ["file.txt"]}]}),
        encoding="utf-8",
    )

    manifest_path = session_dir / "launcher_metadata" / "session_archiver_manifest.json"

    archiver = session_archiver.SessionArchiver(
        session_dir=session_dir,
        network_dir=network_dir,
        backup_dir=backup_dir,
        manifest_path=manifest_path,
        routing_manifest_path=routing_manifest_path,
        include_patterns=["*"],
        exclude_patterns=[],
        dry_run=False,
        skip_completed=False,
        enable_network_copy=True,
        enable_backup_copy=False,
    )

    network_dir.mkdir(parents=True, exist_ok=True)
    archiver.run()

    # instrument.json must be copied to network despite being omitted from routing manifest.
    assert (network_dir / "instrument.json").exists()
    assert (network_dir / "instrument.json").read_text(encoding="utf-8").strip() == '{"instrument": true}'
