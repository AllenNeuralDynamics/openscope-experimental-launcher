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

DEFAULT_EDITOR_IMAGE = "notepad.exe"


def expected_image_from_command(command) -> str:
    """Derive the process image name from an experiment_notes_editor_command
    param (a string, or an iterable whose first element is the executable)."""
    try:
        if isinstance(command, str):
            executable = command
        else:
            executable = str(next(iter(command)))
        name = Path(executable).name
        return name or DEFAULT_EDITOR_IMAGE
    except Exception:  # noqa: BLE001
        return DEFAULT_EDITOR_IMAGE


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


def _query_image_name(pid: int) -> Optional[str]:
    """Return the image name of the process with *pid*, or None if it is not
    running (or the query failed)."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            check=False,
            capture_output=True,
            text=True,
        )
        first_line = (result.stdout or "").strip().splitlines()
        if not first_line:
            return None
        line = first_line[0].strip()
        if not line.startswith('"'):
            # tasklist prints an INFO message instead of CSV when no process matches.
            return None
        import csv

        row = next(csv.reader([line]))
        return row[0] if row else None
    except Exception:  # noqa: BLE001
        return None


def try_close_pid(pid: int, expected_image: Optional[str] = DEFAULT_EDITOR_IMAGE) -> None:
    """Best-effort close of the editor process tree (Windows only).

    PIDs recorded in old notes files can be recycled by the OS to unrelated
    processes, so the process is only killed when its current image name
    matches *expected_image* (case-insensitive). Pass ``expected_image=None``
    to skip the check.
    """
    try:
        if not sys.platform.startswith("win"):
            LOG.info("Not attempting to close notes editor PID %s on non-Windows platform", pid)
            return
        if expected_image is not None:
            image = _query_image_name(pid)
            if image is None:
                LOG.info("Notes editor PID %s is not running; nothing to close.", pid)
                return
            if image.lower() != expected_image.lower():
                LOG.warning(
                    "Refusing to close PID %s: it is running %r, not the expected "
                    "notes editor %r (the recorded PID was likely recycled by the OS).",
                    pid,
                    image,
                    expected_image,
                )
                return
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False, capture_output=True)
        LOG.info("Attempted to close notes editor PID %s", pid)
    except Exception as exc:  # noqa: BLE001
        LOG.warning("Could not close notes editor PID %s: %s", pid, exc)


def close_notes_editor(
    notes_path: Path,
    encoding: str = "utf-8",
    expected_image: Optional[str] = DEFAULT_EDITOR_IMAGE,
) -> bool:
    """Close the notes editor recorded in *notes_path*, if any.

    Best-effort, never raises. Returns True when a PID was found and a close
    was attempted, False otherwise (missing file, no PID line, bad PID). The
    close only terminates a process whose image name matches *expected_image*.
    """
    pid = extract_editor_pid(notes_path, encoding)
    if pid is None:
        return False
    try_close_pid(pid, expected_image=expected_image)
    return True
