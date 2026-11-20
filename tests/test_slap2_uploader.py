"""Tests for the final post-acquisition SLAP2 upload gate."""

import json
from pathlib import Path
import sys
from types import ModuleType

import pytest

from openscope_experimental_launcher.post_acquisition import slap2_uploader


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _ready_session(tmp_path: Path, *, data_status: str = "complete"):
    local_session = tmp_path / "local"
    local_metadata = local_session / "launcher_metadata"
    archive_root = tmp_path / "archive" / "subject_2026-01-02_03-04-05"
    slap2_dir = archive_root / "slap2"
    dynamic_dir = slap2_dir / "dynamic_data"
    dynamic_dir.mkdir(parents=True)

    files = {}
    for filename in ("acquisition_DMD1.meta", "acquisition_DMD1.dat"):
        archived_file = dynamic_dir / filename
        archived_file.write_text("payload", encoding="utf-8")
        files[f"dynamic_data/{filename}"] = {
            "status": data_status,
            "network_copy": True,
            "network_path": str(archived_file),
            "backup_copy": data_status == "complete",
        }

    instrument = slap2_dir / "instrument.json"
    instrument.write_text('{"instrument": true}', encoding="utf-8")
    files["instrument.json"] = {
        "status": "complete",
        "network_copy": True,
        "network_path": str(instrument),
    }

    _write_json(local_metadata / "end_state.json", {"process_returncode": 0})
    _write_json(
        local_metadata / "session_archiver_manifest.json",
        {"network_dir": str(slap2_dir), "files": files},
    )
    return local_session, archive_root, slap2_dir


def _install_fake_onprem(monkeypatch, *, upload_result=None, upload_error=None):
    package = ModuleType("slap2_onprem_handling")
    module = ModuleType("slap2_onprem_handling.upload_slap2")
    calls = {}

    def generate_metadata_jsons(session_id, session_path):
        calls["generate"] = (session_id, Path(session_path))
        (Path(session_path) / "acquisition.json").write_text("{}", encoding="utf-8")
        return "123456", "2026-01-02T03:04:05Z"

    def validate_raw_file_structure(session_path):
        calls["validate"] = Path(session_path)

    def upload_session(session_path, subject_id, session_datetime, **kwargs):
        calls["upload"] = (
            Path(session_path),
            subject_id,
            session_datetime,
            kwargs,
        )
        if upload_error is not None:
            raise upload_error
        return upload_result or {"status_code": 200, "response": {"job_id": "job-1"}}

    module.generate_metadata_jsons = generate_metadata_jsons
    module.validate_raw_file_structure = validate_raw_file_structure
    module.upload_session = upload_session
    package.upload_slap2 = module
    monkeypatch.setitem(sys.modules, "slap2_onprem_handling", package)
    monkeypatch.setitem(sys.modules, "slap2_onprem_handling.upload_slap2", module)
    return calls


def test_disabled_upload_returns_success_without_inspecting_session(tmp_path):
    result = slap2_uploader.run_post_acquisition(
        {"automatic_upload": False, "output_session_folder": str(tmp_path / "missing")}
    )

    assert result == 0
    assert not (tmp_path / "missing").exists()


@pytest.mark.parametrize("missing_name", ["end_state.json", "session_archiver_manifest.json"])
def test_missing_local_preflight_artifact_fails(tmp_path, missing_name):
    local_session, _, _ = _ready_session(tmp_path)
    (local_session / "launcher_metadata" / missing_name).unlink()

    assert slap2_uploader.run_post_acquisition(
        {"automatic_upload": True, "output_session_folder": str(local_session)}
    ) == 2


def test_failed_acquisition_or_incomplete_archive_blocks_upload(tmp_path):
    local_session, _, _ = _ready_session(tmp_path)
    _write_json(
        local_session / "launcher_metadata" / "end_state.json",
        {"process_returncode": 1},
    )
    assert slap2_uploader.run_post_acquisition(
        {"automatic_upload": True, "output_session_folder": str(local_session)}
    ) == 2

    _write_json(
        local_session / "launcher_metadata" / "end_state.json",
        {"process_returncode": 0},
    )
    manifest_path = (
        local_session / "launcher_metadata" / "session_archiver_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["dynamic_data/acquisition_DMD1.dat"]["network_copy"] = False
    _write_json(manifest_path, manifest)
    assert slap2_uploader.run_post_acquisition(
        {"automatic_upload": True, "output_session_folder": str(local_session)}
    ) == 2


def test_pending_backup_is_accepted_and_default_upload_is_dispatched(tmp_path, monkeypatch):
    local_session, archive_root, slap2_dir = _ready_session(
        tmp_path, data_status="pending_backup"
    )
    calls = _install_fake_onprem(monkeypatch)

    result = slap2_uploader.run_post_acquisition(
        {
            "automatic_upload": True,
            "output_session_folder": str(local_session),
            "session_uuid": "session-id",
        }
    )

    assert result == 0
    assert calls["generate"] == ("session-id", archive_root)
    assert calls["validate"] == archive_root
    assert calls["upload"] == (
        archive_root,
        "123456",
        "2026-01-02T03:04:05Z",
        {"force": False},
    )
    assert (archive_root / "instrument.json").read_text(encoding="utf-8") == (
        slap2_dir / "instrument.json"
    ).read_text(encoding="utf-8")
    log_text = (archive_root / "launcher_metadata" / "upload.log").read_text(
        encoding="utf-8"
    )
    assert "Transfer-service dispatch accepted" in log_text
    assert "job-1" in log_text


def test_inline_upload_transfer_settings_are_forwarded_without_schema_duplication(
    tmp_path, monkeypatch
):
    local_session, archive_root, _ = _ready_session(tmp_path)
    calls = _install_fake_onprem(monkeypatch)
    upload_transfer_settings = {
        "run_params": {
            "named_parameters": {"futureParameter": 42},
        },
        "capture_settings": {"tags": ["custom"]},
    }

    result = slap2_uploader.run_post_acquisition(
        {
            "automatic_upload": True,
            "output_session_folder": str(local_session),
            "upload_transfer_settings": upload_transfer_settings,
            "user_email": "operator@aind.org",
        }
    )

    assert result == 0
    assert calls["upload"][3] == {
        "force": False,
        "upload_transfer_settings": upload_transfer_settings,
        "user_email": "operator@aind.org",
    }
    log_text = (archive_root / "launcher_metadata" / "upload.log").read_text(
        encoding="utf-8"
    )
    assert "futureParameter" in log_text
    assert "operator@aind.org" not in log_text


def test_settings_path_is_resolved_relative_to_parameter_pack(tmp_path, monkeypatch):
    local_session, _, _ = _ready_session(tmp_path)
    calls = _install_fake_onprem(monkeypatch)
    pack_dir = tmp_path / "packs"
    settings_path = pack_dir / "upload_settings" / "peakth.json"
    _write_json(
        settings_path,
        {"run_params": {"named_parameters": {"peakth": 7}}},
    )

    result = slap2_uploader.run_post_acquisition(
        {
            "automatic_upload": True,
            "output_session_folder": str(local_session),
            "_parameter_file_directory": str(pack_dir),
            "upload_transfer_settings": "upload_settings/peakth.json",
        }
    )

    assert result == 0
    assert calls["upload"][3]["upload_transfer_settings"] == {
        "run_params": {"named_parameters": {"peakth": 7}}
    }


@pytest.mark.parametrize("settings", ["relative/settings.json", ["invalid"]])
def test_invalid_upload_transfer_settings_fail_preflight(
    tmp_path, monkeypatch, settings
):
    local_session, _, _ = _ready_session(tmp_path)
    calls = _install_fake_onprem(monkeypatch)

    result = slap2_uploader.run_post_acquisition(
        {
            "automatic_upload": True,
            "output_session_folder": str(local_session),
            "upload_transfer_settings": settings,
        }
    )

    assert result == 2
    assert calls.get("upload", []) == []


def test_missing_submitter_email_fails_and_is_logged(tmp_path, monkeypatch):
    local_session, archive_root, _ = _ready_session(tmp_path)
    _install_fake_onprem(
        monkeypatch,
        upload_error=ValueError("A transfer-service user email is required"),
    )

    result = slap2_uploader.run_post_acquisition(
        {"automatic_upload": True, "output_session_folder": str(local_session)}
    )

    assert result == 3
    log_text = (archive_root / "launcher_metadata" / "upload.log").read_text(
        encoding="utf-8"
    )
    assert "user email is required" in log_text


def test_metadata_or_transfer_failure_is_logged(tmp_path, monkeypatch):
    local_session, archive_root, _ = _ready_session(tmp_path)

    class TransferFailure(RuntimeError):
        pass

    failure = TransferFailure("submission rejected")
    failure.response = type(
        "Response", (), {"status_code": 400, "text": "invalid payload"}
    )()
    _install_fake_onprem(monkeypatch, upload_error=failure)

    result = slap2_uploader.run_post_acquisition(
        {"automatic_upload": True, "output_session_folder": str(local_session)}
    )

    assert result == 3
    log_text = (archive_root / "launcher_metadata" / "upload.log").read_text(
        encoding="utf-8"
    )
    assert "submission rejected" in log_text
    assert "HTTP status: 400" in log_text
    assert "invalid payload" in log_text


def test_upload_log_directory_failure_returns_upload_error(
    tmp_path, monkeypatch, caplog
):
    local_session, archive_root, _ = _ready_session(tmp_path)
    calls = _install_fake_onprem(monkeypatch)
    upload_log_parent = archive_root / "launcher_metadata"
    original_mkdir = Path.mkdir

    def fail_upload_log_mkdir(path, *args, **kwargs):
        if path == upload_log_parent:
            raise OSError("network share unavailable")
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fail_upload_log_mkdir)

    result = slap2_uploader.run_post_acquisition(
        {"automatic_upload": True, "output_session_folder": str(local_session)}
    )

    assert result == 3
    assert calls.get("upload", []) == []
    assert "upload.log could not be updated" in caplog.text
