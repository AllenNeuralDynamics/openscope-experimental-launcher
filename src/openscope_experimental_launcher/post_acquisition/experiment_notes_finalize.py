"""Prompt the operator to confirm experiment notes are saved."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Mapping, Optional

from openscope_experimental_launcher.utils import param_utils

LOG = logging.getLogger(__name__)

_DEFAULT_NOTES_FILENAME = "experiment_notes.txt"
_DEFAULT_CONFIRM_PROMPT = (
    "Confirm experiment notes have been saved and the editor is closed. Press Enter to continue."
)


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
            "output_session_folder": "Session output folder that contains experiment notes",
        },
    )


def _resolve_session_dir(params: Mapping[str, Any]) -> Path:
    base = params.get("output_session_folder") or params.get("session_dir")
    if not base:
        raise ValueError("Missing output_session_folder parameter for experiment notes finalize")
    return Path(base).expanduser().resolve()


def _build_notes_path(session_dir: Path, params: Mapping[str, Any]) -> Path:
    notes_filename = params.get("experiment_notes_filename", _DEFAULT_NOTES_FILENAME)
    notes_filename = notes_filename.format(session_folder=str(session_dir))
    path = Path(notes_filename)
    if not path.is_absolute():
        path = session_dir / path
    return path


def run_post_acquisition(param_file: Any = None, overrides: Optional[Mapping[str, Any]] = None) -> int:
    try:
        params = _load_params(param_file, overrides)
        session_dir = _resolve_session_dir(params)
        notes_path = _build_notes_path(session_dir, params)

        if not notes_path.exists():
            LOG.warning("Experiment notes file not found at %s; creating empty file", notes_path)
            notes_path.parent.mkdir(parents=True, exist_ok=True)
            notes_path.touch()

        preview_enabled = params.get("experiment_notes_preview", True)
        preview_limit = params.get("experiment_notes_preview_limit")
        if preview_enabled:
            encoding = params.get("experiment_notes_encoding", "utf-8")
            try:
                raw_content = notes_path.read_text(encoding=encoding)
            except Exception as exc:  # noqa: BLE001
                LOG.warning("Unable to read experiment notes for preview: %s", exc)
            else:
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

        prompt = params.get("experiment_notes_confirm_prompt", _DEFAULT_CONFIRM_PROMPT)
        param_utils.get_user_input(prompt, "")

        LOG.info("Experiment notes finalized at %s", notes_path)
        return 0
    except Exception as exc:  # noqa: BLE001
        LOG.error("Experiment notes finalization failed: %s", exc, exc_info=True)
        return 1