"""Fetch and cache subject procedures from the AIND metadata service."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Optional

from openscope_experimental_launcher.utils import metadata_api, param_utils


_DEFAULT_PROCEDURES_TIMEOUT = 45.0


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
    session_dir = params.get("output_session_folder") or params.get("session_dir")
    if not session_dir:
        raise metadata_api.MetadataServiceError("output_session_folder parameter is required for metadata caching")
    path = Path(session_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _format_payload(payload: Any) -> str:
    if isinstance(payload, (dict, list)):
        return json.dumps(payload, indent=2)
    return str(payload)


def _write_payload(path: Path, payload: Any) -> None:
    path.write_text(_format_payload(payload), encoding="utf-8")


def run_pre_acquisition(param_source: Any, overrides: Optional[Mapping[str, Any]] = None) -> int:  # type: ignore[override]
    params: MutableMapping[str, Any] = {}
    session_folder: Optional[Path] = None
    subject_id = ""
    try:
        params = _load_params(param_source, overrides)
        base_url = metadata_api.resolve_base_url(params)
        timeout = metadata_api.resolve_timeout(params)
        proc_timeout = params.get("metadata_procedures_timeout")
        if proc_timeout is not None:
            try:
                timeout = float(proc_timeout)
            except (TypeError, ValueError):
                logging.warning(
                    "Invalid metadata_procedures_timeout '%s'; using %s seconds instead.",
                    proc_timeout,
                    timeout,
                )
        else:
            timeout = max(timeout, _DEFAULT_PROCEDURES_TIMEOUT)
        subject_id = _resolve_subject_id(params)
        session_folder = _resolve_session_folder(params)

        payload: Any = metadata_api.fetch_json(base_url, f"/api/v2/procedures/{subject_id}", timeout=timeout)
        if not payload:
            raise metadata_api.MetadataServiceError(
                f"No procedures found for subject {subject_id}. Metadata service returned empty response."
            )

        output_path = session_folder / "procedures.json"
        _write_payload(output_path, payload)
        logging.info("Fetched procedures metadata for %s and stored at %s", subject_id, output_path)
        return 0
    except metadata_api.MetadataServiceError as exc:
        if exc.status_code == 400:
            content = exc.payload if exc.payload is not None else exc.body
            if content is None:
                logging.warning(
                    "Procedures metadata returned HTTP 400 for %s with empty response.",
                    subject_id or "<unknown>",
                )
                return 0
            if session_folder is None:
                try:
                    session_folder = _resolve_session_folder(params)
                except Exception:  # noqa: BLE001
                    session_folder = None
            logging.warning(
                "Procedures metadata returned HTTP 400 for %s. Response content:\n%s",
                subject_id,
                _format_payload(content),
            )
            if session_folder:
                output_path = session_folder / "procedures.json"
                _write_payload(output_path, content)
                logging.info(
                    "Stored procedures metadata response for %s at %s despite validation warnings",
                    subject_id or "<unknown>",
                    output_path,
                )
            return 0
        logging.error("Procedures metadata validation failed: %s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        logging.error("Unexpected error during procedures metadata fetch: %s", exc, exc_info=True)
        return 1
