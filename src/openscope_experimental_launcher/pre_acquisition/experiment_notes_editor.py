"""Prepare an experiment notes file and optionally launch a text editor."""
from __future__ import annotations

import logging
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from openscope_experimental_launcher.utils import param_utils

LOG = logging.getLogger(__name__)

_DEFAULT_NOTES_FILENAME = "experiment_notes.txt"


def _load_params(param_source: Any, overrides: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    if isinstance(param_source, Mapping):
        params = dict(param_source)
        if overrides:
            params.update(overrides)
        return params
    return param_utils.load_parameters(
        param_file=param_source,
        overrides=overrides,
        required_fields=["output_session_folder"],
        defaults={},
        help_texts={
            "output_session_folder": "Session output folder where notes should be stored",
        },
    )


def _resolve_session_dir(params: Mapping[str, Any]) -> Path:
    base = params.get("output_session_folder") or params.get("session_dir")
    if not base:
        raise ValueError("Missing output_session_folder parameter for experiment notes editor")
    return Path(base).expanduser().resolve()


def _normalize_args(args: Any) -> list[str]:
    if not args:
        return []
    if isinstance(args, str):
        return shlex.split(args)
    if isinstance(args, Iterable):
        return [str(item) for item in args]
    raise TypeError("experiment_notes_editor_args must be a string or iterable of strings")


def run_pre_acquisition(param_file: Any = None, overrides: Optional[Mapping[str, Any]] = None) -> int:
    try:
        params = _load_params(param_file, overrides)
        session_dir = _resolve_session_dir(params)
        notes_filename = params.get("experiment_notes_filename", _DEFAULT_NOTES_FILENAME)
        notes_filename = notes_filename.format(session_folder=str(session_dir))
        notes_path = Path(notes_filename)
        if not notes_path.is_absolute():
            notes_path = session_dir / notes_path
        notes_path.parent.mkdir(parents=True, exist_ok=True)

        encoding = params.get("experiment_notes_encoding", "utf-8")
        if not notes_path.exists():
            timestamp = datetime.now(timezone.utc).isoformat()
            header = f"# Experiment Notes\n# Created: {timestamp}\n\n"
            notes_path.write_text(header, encoding=encoding)
            LOG.info("Created experiment notes file at %s", notes_path)
        else:
            LOG.info("Using existing experiment notes file at %s", notes_path)

        launch_editor = bool(params.get("experiment_notes_launch_editor", True))
        editor_command_param = params.get("experiment_notes_editor_command", "notepad.exe")
        editor_args = _normalize_args(params.get("experiment_notes_editor_args"))

        command: list[str]
        if isinstance(editor_command_param, str):
            command = [editor_command_param]
        elif isinstance(editor_command_param, Iterable):
            command = [str(part) for part in editor_command_param]
        else:
            raise TypeError("experiment_notes_editor_command must be a string or iterable of strings")

        command = command + editor_args + [str(notes_path)]

        if launch_editor:
            try:
                proc = subprocess.Popen(command)
                LOG.info("Launched experiment notes editor (PID %s)", proc.pid)
            except FileNotFoundError:
                LOG.error("Editor command not found: %s", command[0])
                return 1
            except Exception as exc:  # noqa: BLE001
                LOG.error("Failed to launch editor: %s", exc)
                return 1
        else:
            LOG.info("experiment_notes_launch_editor disabled; not opening external editor")

        return 0
    except Exception as exc:  # noqa: BLE001
        LOG.error("Experiment notes pre-acquisition setup failed: %s", exc, exc_info=True)
        return 1