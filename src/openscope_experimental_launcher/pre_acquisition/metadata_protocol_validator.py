"""Validate protocol identifiers against the AIND metadata service."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping, Optional

from openscope_experimental_launcher.utils import metadata_api, param_utils

_DEFAULT_PROMPT = "Enter protocol identifier"


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


def _resolve_session_folder(params: Mapping[str, Any]) -> Path:
    session_dir = params.get("output_session_folder")
    if not session_dir:
        raise metadata_api.MetadataServiceError("Provide output_session_folder for metadata caching")
    path = Path(str(session_dir)).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _resolve_output_path(params: Mapping[str, Any], session_dir: Path) -> Path:
    explicit = params.get("metadata_protocol_path")
    if explicit:
        path = Path(str(explicit)).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    return session_dir / "protocol.json"


def _initial_protocol_value(params: Mapping[str, Any]) -> Optional[str]:
    module_default = params.get("metadata_protocol_name") or params.get("protocol_name")
    if module_default:
        return str(module_default)
    protocol_param = params.get("protocol_id")
    if isinstance(protocol_param, str):
        return protocol_param
    if isinstance(protocol_param, Iterable):
        for item in protocol_param:
            if item:
                return str(item)
    return None


def _format_payload(payload: Any) -> str:
    if isinstance(payload, (dict, list)):
        return json.dumps(payload, indent=2)
    return str(payload)


def _write_payload(path: Path, payload: Any) -> None:
    path.write_text(_format_payload(payload), encoding="utf-8")


def run_pre_acquisition(param_source: Any, overrides: Optional[Mapping[str, Any]] = None) -> int:  # type: ignore[override]
    params: MutableMapping[str, Any] = {}
    session_folder: Optional[Path] = None
    protocol: Optional[str] = None
    try:
        params = _load_params(param_source, overrides)
        base_url = metadata_api.resolve_base_url(params)
        timeout = metadata_api.resolve_timeout(params)
        session_folder = _resolve_session_folder(params)
        if params.get("metadata_protocol_path"):
            output_path = _resolve_output_path(params, Path.cwd())
        else:
            session_folder = _resolve_session_folder(params)
            output_path = _resolve_output_path(params, session_folder)

        default_protocol = _initial_protocol_value(params)
        prompt = params.get("metadata_protocol_prompt", _DEFAULT_PROMPT)
        protocol = param_utils.get_user_input(prompt, default_protocol)
        if not protocol:
            logging.error("Protocol validation aborted: no protocol identifier provided")
            return 1
        protocol = str(protocol).strip()
        if not protocol:
            logging.error("Protocol validation aborted: protocol identifier is empty")
            return 1

        payload: Any = metadata_api.fetch_json(base_url, f"/api/v2/protocols/{protocol}", timeout=timeout)

        _write_payload(output_path, payload)
        logging.info("Validated protocol '%s' and stored metadata at %s", protocol, output_path)
        return 0
    except metadata_api.MetadataServiceError as exc:
        if exc.status_code == 400:
            content = exc.payload if exc.payload is not None else exc.body
            if content is None:
                logging.warning(
                    "Protocol validation returned HTTP 400 for '%s' with empty response.",
                    protocol or "<unknown>",
                )
                return 0
            if session_folder is None:
                try:
                    session_folder = _resolve_session_folder(params)
                except Exception:  # noqa: BLE001
                    session_folder = None
            logging.warning(
                "Protocol validation returned HTTP 400 for '%s'. Response content:\n%s",
                protocol or "<unknown>",
                _format_payload(content),
            )
            if session_folder:
                output_path = session_folder / "protocol.json"
                _write_payload(output_path, content)
                logging.info(
                    "Stored protocol response for '%s' at %s despite validation warnings",
                    protocol or "<unknown>",
                    output_path,
                )
            return 0
        logging.error("Protocol validation failed: %s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        logging.error("Unexpected error during protocol validation: %s", exc, exc_info=True)
        return 1
