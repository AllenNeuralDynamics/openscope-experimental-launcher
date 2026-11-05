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


def _find_editor_pids_by_cmdline(notes_path: Path, expected_image: str) -> list[int]:
    """Find editor processes by image name + notes file on the command line.

    Windows 11's notepad.exe is a thin alias: the PID the launcher records
    exits immediately after handing the file to the Store Notepad under a
    DIFFERENT pid, so the recorded EditorPID is useless. Recover by scanning
    for live processes whose image matches the expected editor and whose
    command line references the notes file. Best-effort; returns [] when
    psutil is unavailable or nothing matches.
    """
    try:
        import psutil
    except ImportError:
        LOG.info("psutil not available; cannot scan for the notes editor by command line.")
        return []

    notes_name = Path(notes_path).name.lower()
    notes_full = str(notes_path).lower()
    pids: list[int] = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = (proc.info.get("name") or "")
            if name.lower() != expected_image.lower():
                continue
            cmdline = " ".join(proc.info.get("cmdline") or []).lower()
            if notes_full in cmdline or notes_name in cmdline:
                pids.append(proc.info["pid"])
        except Exception:  # noqa: BLE001  (process may vanish mid-iteration)
            continue
    return pids


def _any_process_with_image(expected_image: str) -> bool:
    """Whether any live process runs *expected_image* (best-effort)."""
    try:
        import psutil
    except ImportError:
        return False
    for proc in psutil.process_iter(["name"]):
        try:
            if (proc.info.get("name") or "").lower() == expected_image.lower():
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


def close_notes_editor(
    notes_path: Path,
    encoding: str = "utf-8",
    expected_image: Optional[str] = DEFAULT_EDITOR_IMAGE,
) -> bool:
    """Close the editor that has *notes_path* open, if any.

    Tries the ``# EditorPID:`` recorded in the notes header first; when that
    process is already gone (e.g. Windows 11 notepad hands off to the Store
    app under a different pid) falls back to scanning for live processes
    running the expected editor image with the notes file on their command
    line. Best-effort, never raises. Returns True when an editor process was
    found and a close was attempted.

    LIMITATION: Windows 11 Notepad hosts ALL open files as tabs inside one
    shared process whose command line references none of them. That process
    is deliberately never killed — it may hold unrelated unsaved tabs — so
    when it is detected, a console hint asks the operator to close the notes
    tab themselves.
    """
    if not Path(notes_path).exists():
        return False

    attempted = False

    pid = extract_editor_pid(notes_path, encoding)
    if pid is not None:
        image = _query_image_name(pid)
        if image is not None and (
            expected_image is None or image.lower() == expected_image.lower()
        ):
            try_close_pid(pid, expected_image=expected_image)
            attempted = True

    if not attempted and expected_image and sys.platform.startswith("win"):
        for found_pid in _find_editor_pids_by_cmdline(notes_path, expected_image):
            LOG.info(
                "Recorded EditorPID was stale; found %s (PID %s) holding %s via command line.",
                expected_image,
                found_pid,
                notes_path,
            )
            try_close_pid(found_pid, expected_image=expected_image)
            attempted = True

    if not attempted and expected_image and sys.platform.startswith("win"):
        if _any_process_with_image(expected_image):
            message = (
                f"{expected_image} is running but the window holding the "
                f"experiment notes could not be identified (Windows 11 Notepad "
                "keeps all files as tabs in one shared process, which will not "
                "be force-closed because it may hold unrelated unsaved work). "
                "Please save and close the experiment-notes tab yourself."
            )
            LOG.warning(message)
            print("\nNOTE: " + message)

    return attempted
