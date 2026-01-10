"""Fetch and cache subject metadata from the AIND metadata service."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Optional

from openscope_experimental_launcher.utils import metadata_api, param_utils


def _load_params(param_source: Any, overrides: Optional[Mapping[str, Any]] = None) -> MutableMapping[str, Any]:
    if isinstance(param_source, Mapping):
        params = dict(param_source)
        if overrides:
            params.update(overrides)
        return params
    params = param_utils.load_parameters(param_file=param_source)
    if overrides:
        params.update(overrides)
    return params


def _resolve_subject_id(params: Mapping[str, Any]) -> str:
    overrides = params.get("metadata_subject_id") or params.get("metadata_mouse_id")
    if overrides:
        return str(overrides)
    subject_id = params.get("subject_id") or params.get("mouse_id")
    if not subject_id:
        raise metadata_api.MetadataServiceError(
            "Subject ID not found. Provide 'subject_id' or set 'metadata_subject_id' in module_parameters."
        )
    return str(subject_id)


def _resolve_session_folder(params: Mapping[str, Any]) -> Path:
    session_dir = params.get("session_dir") or params.get("output_session_folder")
    if not session_dir:
        raise metadata_api.MetadataServiceError("Provide session_dir or output_session_folder for metadata caching")
    path = Path(session_dir).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _resolve_output_path(params: Mapping[str, Any], session_dir: Path) -> Path:
    explicit = params.get("metadata_subject_path")
    if explicit:
        path = Path(str(explicit)).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    return session_dir / "subject.json"


def _format_payload(payload: Any) -> str:
    if isinstance(payload, (dict, list)):
        return json.dumps(payload, indent=2)
    return str(payload)


def _write_payload(path: Path, payload: Any) -> None:
    content = _format_payload(payload)
    path.write_text(content, encoding="utf-8")


def run_pre_acquisition(param_source: Any, overrides: Optional[Mapping[str, Any]] = None) -> int:  # type: ignore[override]
    params: MutableMapping[str, Any] = {}
    session_folder: Optional[Path] = None
    subject_id = ""
    try:
        params = _load_params(param_source, overrides)
        base_url = metadata_api.resolve_base_url(params)
        timeout = metadata_api.resolve_timeout(params)
        subject_id = _resolve_subject_id(params)
        session_folder: Optional[Path] = None
        output_path: Path
        if params.get("metadata_subject_path"):
            output_path = _resolve_output_path(params, Path.cwd())
        else:
            session_folder = _resolve_session_folder(params)
            output_path = _resolve_output_path(params, session_folder)

        payload: Any = metadata_api.fetch_json(base_url, f"/api/v2/subject/{subject_id}", timeout=timeout)
        _write_payload(output_path, payload)
        logging.info("Fetched subject metadata for %s and stored at %s", subject_id, output_path)
        return 0
    except metadata_api.MetadataServiceError as exc:
        if exc.status_code == 400:
            content = exc.payload if exc.payload is not None else exc.body
            if content is None:
                logging.warning(
                    "Subject metadata validation returned HTTP 400 for %s with empty response.",
                    subject_id or "<unknown>",
                )
                return 0
            if session_folder is None:
                try:
                    session_folder = _resolve_session_folder(params)
                except Exception:  # noqa: BLE001
                    session_folder = None
            logging.warning(
                "Subject metadata validation returned HTTP 400 for %s. Response content:\n%s",
                subject_id,
                _format_payload(content),
            )
            if session_folder:
                output_path = session_folder / "subject.json"
                _write_payload(output_path, content)
                logging.info(
                    "Stored subject metadata response for %s at %s despite validation warnings",
                    subject_id or "<unknown>",
                    output_path,
                )
            return 0
        logging.error("Subject metadata validation failed: %s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        logging.error("Unexpected error during subject metadata fetch: %s", exc, exc_info=True)
        return 1
