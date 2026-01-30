"""Prepare an experiment notes file and optionally launch a text editor."""
from __future__ import annotations

import logging
import shlex
import subprocess
from datetime import datetime
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
    return param_utils.load_parameters(param_file=param_source, overrides=overrides)


def _resolve_notes_path(params: Mapping[str, Any]) -> Path:
    filename = params.get("experiment_notes_filename", _DEFAULT_NOTES_FILENAME)
    path = Path(str(filename)).expanduser()
    if not path.is_absolute():
        base = params.get("output_session_folder")
        if not base:
            raise ValueError("output_session_folder is required to resolve experiment notes path")
        path = (Path(str(base)).expanduser() / path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _ensure_header_with_pid(notes_path: Path, encoding: str, pid: int) -> None:
    """Add header metadata with the editor PID if not present."""
    pid_line = f"# EditorPID: {pid}\n"
    if notes_path.exists():
        try:
            content = notes_path.read_text(encoding=encoding)
        except Exception:  # noqa: BLE001
            return
        if "EditorPID:" in content:
            return
        notes_path.write_text(pid_line + content, encoding=encoding)
    else:
        timestamp = datetime.now().astimezone().isoformat()
        header = f"# Experiment Notes\n# Created: {timestamp}\n{pid_line}\n"
        notes_path.write_text(header, encoding=encoding)


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
        notes_path = _resolve_notes_path(params)

        encoding = params.get("experiment_notes_encoding", "utf-8")
        if notes_path.exists():
            LOG.info("Using existing experiment notes file at %s", notes_path)
        else:
            timestamp = datetime.now().astimezone().isoformat()
            header = f"# Experiment Notes\n# Created: {timestamp}\n\n"
            notes_path.write_text(header, encoding=encoding)
            LOG.info("Created experiment notes file at %s", notes_path)

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
                if proc.pid:
                    _ensure_header_with_pid(notes_path, encoding, proc.pid)
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