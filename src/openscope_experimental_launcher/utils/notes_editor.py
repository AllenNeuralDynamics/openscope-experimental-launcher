"""Helpers for managing the experiment-notes editor process.

The notes step opens a text editor on the rig and records its PID in the
notes file on a ``# EditorPID:`` line. These helpers let later steps
(experiment_notes_finalize, slap2_meta_annotator) close that editor so it
does not hold the file open or clutter the operator's screen. Everything
here is best-effort and never raises.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

LOG = logging.getLogger(__name__)

_EDITOR_PID_PREFIX = "# EditorPID:"


def extract_editor_pid(notes_path: Path, encoding: str = "utf-8") -> Optional[int]:
    """Return the PID recorded on the ``# EditorPID:`` line, if any."""
    try:
        text = Path(notes_path).read_text(encoding=encoding)
    except Exception:  # noqa: BLE001
        return None
    for line in text.splitlines():
        if line.startswith(_EDITOR_PID_PREFIX):
            try:
                return int(line.split(":", 1)[1].strip())
            except Exception:  # noqa: BLE001
                return None
    return None


def try_close_pid(pid: int) -> None:
    """Best-effort close of the editor process tree (Windows only)."""
    try:
        if not sys.platform.startswith("win"):
            LOG.info("Not attempting to close notes editor PID %s on non-Windows platform", pid)
            return
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False, capture_output=True)
        LOG.info("Attempted to close notes editor PID %s", pid)
    except Exception as exc:  # noqa: BLE001
        LOG.warning("Could not close notes editor PID %s: %s", pid, exc)


def close_notes_editor(notes_path: Path, encoding: str = "utf-8") -> bool:
    """Close the notes editor recorded in *notes_path*, if any.

    Best-effort, never raises. Returns True when a PID was found and a close
    was attempted, False otherwise (missing file, no PID line, bad PID).
    """
    pid = extract_editor_pid(notes_path, encoding)
    if pid is None:
        return False
    try_close_pid(pid)
    return True
