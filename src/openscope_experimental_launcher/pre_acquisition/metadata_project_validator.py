"""Validate project names against the AIND metadata service."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Optional

from openscope_experimental_launcher.utils import metadata_api, param_utils

_DEFAULT_PROMPT = "Select project name from metadata service"


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
    session_dir = params.get("output_session_folder") or params.get("session_dir")
    if not session_dir:
        raise metadata_api.MetadataServiceError("output_session_folder parameter is required for metadata caching")
    path = Path(session_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _initial_project_value(params: Mapping[str, Any]) -> Optional[str]:
    module_value = params.get("metadata_project_name") or params.get("project_name")
    if module_value:
        return str(module_value)
    projects = params.get("projects")
    if isinstance(projects, list) and projects:
        return str(projects[0])
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
    try:
        params = _load_params(param_source, overrides)
        base_url = metadata_api.resolve_base_url(params)
        timeout = metadata_api.resolve_timeout(params)
        session_folder = _resolve_session_folder(params)

        default_project = _initial_project_value(params)
        prompt = params.get("metadata_project_prompt", _DEFAULT_PROMPT)
        initial_project = params.get("metadata_project_name")
        if initial_project is None:
            initial_project = param_utils.get_user_input(prompt, default_project)
        if initial_project is not None:
            initial_project = str(initial_project).strip()
        project_name = initial_project if initial_project else None

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

        output_path = session_folder / "project.json"
        output_path.write_text(
            json.dumps({"project_name": project_name}, indent=2), encoding="utf-8"
        )
        logging.info("Validated project '%s' via metadata service and stored selection at %s", project_name, output_path)
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
                record = {"project_name": project_name}
                record["metadata_response"] = payload
                _write_payload(output_path, record)
                logging.info(
                    "Stored project selection for '%s' at %s despite validation warnings",
                    project_name or "<unknown>",
                    output_path,
                )
            return 0
        logging.error("Project validation failed: %s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        logging.error("Unexpected error during project validation: %s", exc, exc_info=True)
        return 1
