"""Prompt the operator to confirm experiment notes are saved."""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Optional

from openscope_experimental_launcher.utils import param_utils

LOG = logging.getLogger(__name__)

_DEFAULT_NOTES_FILENAME = "experiment_notes.txt"
_DEFAULT_CONFIRM_PROMPT = (
    "Confirm experiment notes have been saved and the editor is closed. Type 'yes' to continue."
)


def _load_params(param_source: Any, overrides: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    if isinstance(param_source, Mapping):
        params = dict(param_source)
        if overrides:
            params.update(overrides)
        return params
    return param_utils.load_parameters(param_file=param_source, overrides=overrides)


def _resolve_notes_path(params: Mapping[str, Any]) -> Path:
    notes_filename = params.get("experiment_notes_filename", _DEFAULT_NOTES_FILENAME)
    path = Path(str(notes_filename)).expanduser()
    if not path.is_absolute():
        base = params.get("output_session_folder")
        if not base:
            raise ValueError("output_session_folder is required to resolve experiment notes path")
        path = (Path(str(base)).expanduser() / path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _extract_editor_pid(notes_path: Path, encoding: str) -> Optional[int]:
    try:
        text = notes_path.read_text(encoding=encoding)
    except Exception:  # noqa: BLE001
        return None
    for line in text.splitlines():
        if line.startswith("# EditorPID:"):
            try:
                return int(line.split(":", 1)[1].strip())
            except Exception:  # noqa: BLE001
                return None
    return None


def _show_preview(notes_path: Path, encoding: str, preview_limit: Optional[int]) -> None:
    try:
        raw_content = notes_path.read_text(encoding=encoding)
    except Exception as exc:  # noqa: BLE001
        LOG.warning("Unable to read experiment notes for preview: %s", exc)
        return
    content = raw_content
    truncated = False
    if isinstance(preview_limit, int) and preview_limit > 0 and len(content) > preview_limit:
        content = content[:preview_limit]
        truncated = True
    divider = "-" * 60
    display = content if content else "[File is empty]"
    LOG.info("%s\nExperiment notes preview (%s):\n%s\n%s", divider, notes_path, display, divider)
    if truncated:
        LOG.info(
            "Preview truncated to first %s characters; adjust experiment_notes_preview_limit to see more.",
            preview_limit,
        )


def _confirm_yes(prompt: str, prompt_func, *, allow_no: bool, max_attempts: Optional[int]) -> bool:
    attempts = 0
    limit = max_attempts if max_attempts is not None else 3
    while True:
        resp = prompt_func(prompt, "")
        if resp is None:
            continue
        text = str(resp).strip().lower()
        if text in {"yes", "y", ""}:
            return True
        if text in {"no", "n"}:
            if allow_no:
                LOG.info("Confirmation declined; exiting experiment notes finalization.")
                return False
            attempts += 1
            if limit is not None and attempts >= limit:
                LOG.error("Confirmation not received after %s attempt(s); aborting.", attempts)
                return False
            LOG.info("Confirmation declined; please review notes and confirm again.")
            continue


def _try_close_pid(pid: int) -> None:
    try:
        if not sys.platform.startswith("win"):
            LOG.info("Not attempting to close notes editor PID %s on non-Windows platform", pid)
            return
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False, capture_output=True)
        LOG.info("Attempted to close notes editor PID %s", pid)
    except Exception as exc:  # noqa: BLE001
        LOG.warning("Could not close notes editor PID %s: %s", pid, exc)


def run_post_acquisition(param_file: Any = None, overrides: Optional[Mapping[str, Any]] = None) -> int:
    try:
        params = _load_params(param_file, overrides)
        notes_path = _resolve_notes_path(params)

        if not notes_path.exists():
            LOG.warning("Experiment notes file not found at %s; creating empty file", notes_path)
            notes_path.parent.mkdir(parents=True, exist_ok=True)
            notes_path.touch()

        preview_enabled = params.get("experiment_notes_preview", True)
        preview_limit = params.get("experiment_notes_preview_limit")
        encoding = params.get("experiment_notes_encoding", "utf-8")
        if preview_enabled:
            _show_preview(notes_path, encoding, preview_limit)

        prompt = params.get("experiment_notes_confirm_prompt", _DEFAULT_CONFIRM_PROMPT)
        allow_no = bool(params.get("experiment_notes_allow_no", False))
        max_attempts = params.get("experiment_notes_confirm_max_attempts")
        _show_preview(notes_path, encoding, preview_limit)  # fresh preview before confirmation
        confirmed = _confirm_yes(prompt, param_utils.get_user_input, allow_no=allow_no, max_attempts=max_attempts)
        if not confirmed:
            return 1

        if params.get("experiment_notes_autoclose_editor", True):
            pid = _extract_editor_pid(notes_path, encoding)
            if pid:
                _try_close_pid(pid)

        LOG.info("Experiment notes finalized at %s", notes_path)
        return 0
    except Exception as exc:  # noqa: BLE001
        LOG.error("Experiment notes finalization failed: %s", exc, exc_info=True)
        return 1