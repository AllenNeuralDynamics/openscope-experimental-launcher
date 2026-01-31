"""Validate project names against the AIND metadata service."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Optional

from openscope_experimental_launcher.utils import metadata_api, param_utils

_DEFAULT_PROMPT = "Select project name from metadata service"
_DEFAULT_PROTOCOL_PROMPT = "Confirm animal protocol identifier"
_DEFAULT_OPERATOR_PROMPT = "Confirm operator name"


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
    explicit = params.get("metadata_project_path")
    if explicit:
        path = Path(str(explicit)).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    return session_dir / "project.json"


def _initial_project_value(params: Mapping[str, Any]) -> Optional[str]:
    module_value = params.get("metadata_project_name") or params.get("project_name")
    if module_value:
        return str(module_value)
    projects = params.get("projects")
    if isinstance(projects, list) and projects:
        return str(projects[0])
    return None


def _initial_protocol_value(params: Mapping[str, Any]) -> Optional[str]:
    protocol_param = params.get("protocol_id")
    if isinstance(protocol_param, str):
        return protocol_param
    if isinstance(protocol_param, (list, tuple)):
        for item in protocol_param:
            if item:
                return str(item)
    return None


def _initial_operator_value(params: Mapping[str, Any]) -> Optional[str]:
    operator = params.get("operator") or params.get("user_id")
    if operator:
        return str(operator)
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
    project_name: Optional[str] = None
    protocol_id: Optional[str] = None
    operator_name: Optional[str] = None
    try:
        params = _load_params(param_source, overrides)
        base_url = metadata_api.resolve_base_url(params)
        timeout = metadata_api.resolve_timeout(params)
        if params.get("metadata_project_path"):
            output_path = _resolve_output_path(params, Path.cwd())
        else:
            session_folder = _resolve_session_folder(params)
            output_path = _resolve_output_path(params, session_folder)

        default_project = _initial_project_value(params)
        prompt = params.get("metadata_project_prompt", _DEFAULT_PROMPT)
        initial_project = param_utils.get_user_input(prompt, default_project or "")
        if initial_project is not None:
            initial_project = str(initial_project).strip()
            if not initial_project:
                initial_project = None
        project_name = initial_project if initial_project else None

        protocol_prompt = params.get("metadata_protocol_prompt", _DEFAULT_PROTOCOL_PROMPT)
        default_protocol = _initial_protocol_value(params)
        protocol_raw = param_utils.get_user_input(protocol_prompt, default_protocol or "")
        if protocol_raw is not None:
            protocol_id = str(protocol_raw).strip()
            if not protocol_id:
                protocol_id = None
        if not protocol_id:
            logging.error("Protocol confirmation aborted: no protocol identifier provided")
            return 1

        operator_prompt = params.get("metadata_operator_prompt", _DEFAULT_OPERATOR_PROMPT)
        default_operator = _initial_operator_value(params)
        operator_raw = param_utils.get_user_input(operator_prompt, default_operator or "")
        if operator_raw is not None:
            operator_name = str(operator_raw).strip()
            if not operator_name:
                operator_name = None
        if not operator_name:
            logging.warning("Operator not provided; proceeding without operator in project.json")

        available_projects_raw = metadata_api.fetch_json(base_url, "/api/v2/project_names", timeout=timeout)
        if not isinstance(available_projects_raw, list):
            raise metadata_api.MetadataServiceError("Project names endpoint returned unexpected payload")

        available_projects = [str(name).strip() for name in available_projects_raw if str(name).strip()]
        if not available_projects:
            raise metadata_api.MetadataServiceError("Project names endpoint returned no projects")

        normalized_map = {proj.lower(): proj for proj in available_projects}

        def _select_project(initial: Optional[str]) -> Optional[str]:
            if initial:
                candidate = initial.strip()
                if candidate and candidate.lower() in normalized_map:
                    return normalized_map[candidate.lower()]
            logging.warning(
                "Project '%s' not found in metadata service. Available projects will be displayed for selection.",
                initial or "<none>",
            )
            formatted = "\n".join(f"- {proj}" for proj in available_projects)
            logging.info("Available projects from metadata service:\n%s", formatted)
            max_attempts = 5
            default_choice = available_projects[0]
            attempts = 0
            while attempts < max_attempts:
                choice = param_utils.get_user_input(prompt, default_choice)
                if choice:
                    normalized = str(choice).strip().lower()
                    if normalized in normalized_map:
                        return normalized_map[normalized]
                attempts += 1
                logging.error(
                    "Project selection '%s' not recognized. %s attempt(s) remaining.",
                    choice or "<empty>",
                    max_attempts - attempts,
                )
            return None

        resolved_project = _select_project(initial_project)
        if not resolved_project:
            logging.error("Project validation aborted: unable to select a valid project name")
            return 1
        project_name = resolved_project

        output_path.write_text(
            json.dumps({"project_name": project_name, "protocol_id": protocol_id, "operator": operator_name}, indent=2),
            encoding="utf-8",
        )
        logging.info(
            "Validated project '%s', confirmed protocol '%s', operator '%s'; stored selection at %s",
            project_name,
            protocol_id,
            operator_name or "<none>",
            output_path,
        )
        return 0
    except metadata_api.MetadataServiceError as exc:
        if exc.status_code == 400:
            payload = exc.payload if exc.payload is not None else exc.body or ""
            if session_folder is None:
                try:
                    session_folder = _resolve_session_folder(params)
                except Exception:  # noqa: BLE001
                    session_folder = None
            logging.warning(
                "Project validation returned HTTP 400 for '%s'. Response content:\n%s",
                project_name or "<unknown>",
                _format_payload(payload),
            )
            if session_folder:
                output_path = session_folder / "project.json"
                record = {"project_name": project_name, "protocol_id": protocol_id, "operator": operator_name}
                record["metadata_response"] = payload
                _write_payload(output_path, record)
                logging.info(
                    "Stored project selection for '%s' (protocol '%s', operator '%s') at %s despite validation warnings",
                    project_name or "<unknown>",
                    protocol_id or "<unknown>",
                    operator_name or "<none>",
                    output_path,
                )
            return 0
        logging.error("Project validation failed: %s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        logging.error("Unexpected error during project validation: %s", exc, exc_info=True)
        return 1
