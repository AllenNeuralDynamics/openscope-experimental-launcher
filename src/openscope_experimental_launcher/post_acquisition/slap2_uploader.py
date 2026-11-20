"""Upload an archived SLAP2 session after successful acquisition and archival."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import shutil
import traceback
from typing import Any, Mapping

LOG = logging.getLogger(__name__)

_DATA_DIRS = {"dynamic_data", "static_data"}
_REQUIRED_DATA_SUFFIXES = {".dat", ".meta"}


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    """Read a required JSON object with an actionable error message."""
    if not path.is_file():
        raise FileNotFoundError(f"Missing {label}: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Invalid {label}: expected a JSON object in {path}")
    return value


def _resolve_upload_transfer_settings(
    value: Any, *, parameter_file_directory: str | None
) -> dict[str, Any] | None:
    """Return inline settings or load a JSON path relative to the parameter pack."""
    if value is None:
        return None
    if isinstance(value, Mapping):
        return dict(value)
    if not isinstance(value, str):
        raise TypeError(
            "upload_transfer_settings must be a JSON object or JSON file path"
        )
    settings_path = Path(value)
    if not settings_path.is_absolute():
        if not parameter_file_directory:
            raise ValueError(
                "a relative upload_transfer_settings path requires the original "
                "parameter-pack directory"
            )
        settings_path = Path(parameter_file_directory) / settings_path
    return _read_json_object(
        settings_path.resolve(), label="upload transfer settings"
    )


def _archived_paths(manifest: Mapping[str, Any]) -> tuple[Path, Path]:
    """Return the archived session root and its SLAP2 modality directory."""
    network_value = manifest.get("network_dir")
    if not network_value:
        raise ValueError("Archiver manifest does not record network_dir")

    network_dir = Path(str(network_value))
    if network_dir.name.casefold() == "slap2":
        return network_dir.parent, network_dir
    return network_dir, network_dir / "slap2"


def _verify_archived_inputs(manifest: Mapping[str, Any], slap2_dir: Path) -> None:
    """Require verified network copies for the SLAP2 data selected for upload."""
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Archiver manifest has no file records")

    copied_suffixes: set[str] = set()
    for relative_name, raw_entry in files.items():
        if not isinstance(raw_entry, dict):
            raise ValueError(f"Invalid archiver record for {relative_name!r}")

        relative_path = Path(str(relative_name))
        is_slap2_data = bool(relative_path.parts) and (
            relative_path.parts[0] in _DATA_DIRS
        )
        if not is_slap2_data:
            continue

        status = raw_entry.get("status")
        if status not in {"complete", "pending_backup"}:
            raise ValueError(
                f"SLAP2 archive record {relative_name!r} has status {status!r}"
            )
        if raw_entry.get("network_copy") is not True:
            raise ValueError(
                f"SLAP2 archive record {relative_name!r} has no verified network copy"
            )

        network_path = raw_entry.get("network_path")
        expected_path = slap2_dir / relative_path
        copied_path = Path(str(network_path)) if network_path else expected_path
        if not copied_path.is_file():
            raise FileNotFoundError(
                f"Archived SLAP2 file is missing for {relative_name!r}: {copied_path}"
            )
        if relative_path.suffix.casefold() in _REQUIRED_DATA_SUFFIXES:
            copied_suffixes.add(relative_path.suffix.casefold())

    missing = sorted(_REQUIRED_DATA_SUFFIXES - copied_suffixes)
    if missing:
        raise ValueError(
            "Archived SLAP2 input is incomplete; no verified network copy for "
            + ", ".join(missing)
        )


def _write_event(handle, message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    print(f"[{timestamp}] {message}", file=handle, flush=True)


def _log_http_error(handle, exc: BaseException) -> None:
    response = getattr(exc, "response", None)
    if response is None:
        return
    _write_event(handle, f"HTTP status: {getattr(response, 'status_code', 'unknown')}")
    body = getattr(response, "text", None)
    if body:
        _write_event(handle, f"HTTP response body: {body}")


def _copy_root_instrument_if_needed(session_root: Path, slap2_dir: Path) -> None:
    """Promote the archived rig instrument file to the AIND session root."""
    destination = session_root / "instrument.json"
    source = slap2_dir / "instrument.json"
    if not destination.exists() and source.is_file():
        shutil.copy2(source, destination)


def run_post_acquisition(
    params: Mapping[str, Any],
    overrides: Mapping[str, Any] | None = None,
) -> int:
    """Generate metadata and dispatch transfer for a safely archived session."""
    merged = dict(params)
    if overrides:
        merged.update(overrides)

    if merged.get("automatic_upload") is not True:
        LOG.info("Automatic SLAP2 upload is disabled; skipping upload")
        return 0

    session_value = merged.get("output_session_folder") or merged.get("session_dir")
    if not session_value:
        LOG.error("Automatic upload requires output_session_folder or session_dir")
        return 2

    local_session = Path(str(session_value))
    local_metadata = local_session / "launcher_metadata"
    manifest_path = local_metadata / "session_archiver_manifest.json"
    end_state_path = local_metadata / "end_state.json"

    try:
        end_state = _read_json_object(end_state_path, label="launcher end state")
        if end_state.get("process_returncode") != 0:
            raise ValueError(
                "Acquisition did not complete successfully: "
                f"process_returncode={end_state.get('process_returncode')!r}"
            )
        manifest = _read_json_object(manifest_path, label="archiver manifest")
        session_root, slap2_dir = _archived_paths(manifest)
        _verify_archived_inputs(manifest, slap2_dir)
    except Exception as exc:  # noqa: BLE001 - module boundary reports failure
        LOG.error("Automatic SLAP2 upload preflight failed: %s", exc, exc_info=True)
        return 2

    try:
        upload_transfer_settings = _resolve_upload_transfer_settings(
            merged.get("upload_transfer_settings"),
            parameter_file_directory=merged.get("_parameter_file_directory"),
        )
    except Exception as exc:  # noqa: BLE001 - configuration boundary
        LOG.error("Invalid upload_transfer_settings: %s", exc, exc_info=True)
        return 2
    user_email = merged.get("user_email")
    if user_email is not None and not isinstance(user_email, str):
        LOG.error("user_email must be a string when provided")
        return 2

    upload_log = session_root / "launcher_metadata" / "upload.log"

    try:
        upload_log.parent.mkdir(parents=True, exist_ok=True)
        with upload_log.open("a", encoding="utf-8", buffering=1) as handle:
            _write_event(handle, "Automatic SLAP2 upload started")
            _write_event(handle, f"Archived session root: {session_root}")
            if upload_transfer_settings:
                _write_event(
                    handle,
                    "Upload transfer setting overrides: "
                    + json.dumps(
                        upload_transfer_settings, sort_keys=True, default=str
                    ),
                )
            if user_email:
                _write_event(handle, "Transfer submitter email: <configured>")

            with redirect_stdout(handle), redirect_stderr(handle):
                from slap2_onprem_handling.upload_slap2 import (
                    generate_metadata_jsons,
                    upload_session,
                    validate_raw_file_structure,
                )

                _write_event(handle, "Metadata generation started")
                _copy_root_instrument_if_needed(session_root, slap2_dir)
                subject_id, session_datetime = generate_metadata_jsons(
                    str(merged.get("session_uuid") or session_root.name),
                    session_root,
                )
                validate_raw_file_structure(session_root)
                _write_event(handle, "Metadata generation and local validation completed")

                _write_event(handle, "Transfer-service dispatch started")
                upload_kwargs: dict[str, Any] = {"force": False}
                if upload_transfer_settings is not None:
                    upload_kwargs["upload_transfer_settings"] = (
                        upload_transfer_settings
                    )
                if user_email is not None:
                    upload_kwargs["user_email"] = user_email
                result = upload_session(
                    session_root,
                    subject_id,
                    session_datetime,
                    **upload_kwargs,
                )
                _write_event(
                    handle,
                    "Transfer-service dispatch accepted: "
                    + json.dumps(result, sort_keys=True, default=str),
                )
                _write_event(handle, "Automatic SLAP2 upload completed successfully")
        return 0
    except Exception as exc:  # noqa: BLE001 - preserve full post-acquisition record
        try:
            with upload_log.open("a", encoding="utf-8", buffering=1) as handle:
                _write_event(handle, f"Automatic SLAP2 upload failed: {exc}")
                _log_http_error(handle, exc)
                traceback.print_exc(file=handle)
        except OSError:
            LOG.exception("Automatic upload failed and upload.log could not be updated")
        LOG.error("Automatic SLAP2 upload failed; see %s", upload_log, exc_info=True)
        return 3
