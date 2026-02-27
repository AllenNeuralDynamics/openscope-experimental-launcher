"""Fetch the latest instrument.json and copy it into the session folder.

This pre-acquisition module is intended for SLAP2 workflows.

Behavior:
- Finds the most recently modified instrument.json under a configured source root.
- Shows the chosen file path + modification time for operator confirmation.
- Allows the operator to override by providing an alternate file path.
- Copies the selected file to the *root* of the current session folder.

Typical configuration (in a param pack):

    {
      "module_type": "launcher_module",
      "module_path": "instrument_json_fetch",
      "module_parameters": {
        "instrument_json_source_root": "C:/Users/ScanImage/Documents/GitHub/slap2_processing"
      }
    }

"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Optional

LOG = logging.getLogger(__name__)

DEFAULT_SOURCE_ROOT = "C:/Users/ScanImage/Documents/GitHub/slap2_processing"
DEFAULT_FILENAME = "instrument.json"
DEFAULT_DEST_NAME = "instrument.json"


def _prompt(message: str) -> str:
    try:
        return input(message)
    except (EOFError, OSError):
        return ""


def _prompt_yes_no(message: str, *, default_yes: bool = True, assume_yes: bool = False) -> bool:
    if assume_yes:
        return default_yes

    suffix = "(Y/n)" if default_yes else "(y/N)"
    while True:
        raw = _prompt(f"{message} {suffix}: ").strip().lower()
        if not raw:
            return default_yes
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("Please enter y or n.")


def _format_mtime(path: Path) -> str:
    try:
        ts = path.stat().st_mtime
    except OSError:
        return "<unknown>"
    try:
        # On some Windows/Python combinations, very small timestamps can raise
        # OSError during tz conversion. This is display-only, so be defensive.
        return datetime.fromtimestamp(ts).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    except (OSError, OverflowError, ValueError):
        return "<unknown>"


def _resolve_session_dir(params: Mapping[str, Any]) -> Path:
    session_dir = params.get("output_session_folder")
    if not session_dir:
        raise ValueError("output_session_folder is required")
    path = Path(str(session_dir)).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _resolve_source_root(params: Mapping[str, Any]) -> Path:
    value = params.get("instrument_json_source_root") or DEFAULT_SOURCE_ROOT
    return Path(str(value)).expanduser()


def _resolve_explicit_source_path(params: Mapping[str, Any]) -> Optional[Path]:
    value = params.get("instrument_json_source_path")
    if not value:
        return None
    return Path(str(value)).expanduser()


def _find_latest_instrument_json(root: Path, *, filename: str, recursive: bool) -> Optional[Path]:
    if root.is_file():
        return root

    if not root.exists() or not root.is_dir():
        return None

    candidates: list[Path] = []

    direct = root / filename
    if direct.exists() and direct.is_file():
        candidates.append(direct)

    if recursive:
        candidates.extend([p for p in root.rglob(filename) if p.is_file()])

    if not candidates:
        return None

    # Pick most recently modified file.
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _prompt_for_alternate_path(*, assume_yes: bool) -> Optional[Path]:
    if assume_yes:
        return None

    while True:
        raw = _prompt("Enter path to instrument.json (blank to cancel): ").strip().strip('"')
        if not raw:
            return None
        candidate = Path(raw).expanduser()
        if candidate.exists() and candidate.is_file():
            return candidate
        print(f"File not found: {candidate}")


def run_pre_acquisition(params: Mapping[str, Any]) -> int:
    """Copy a selected instrument.json into the current session folder."""

    assume_yes = bool(params.get("assume_yes", False))
    required = bool(params.get("instrument_json_required", True))
    recursive = bool(params.get("instrument_json_recursive", True))
    filename = str(params.get("instrument_json_filename") or DEFAULT_FILENAME)
    dest_name = str(params.get("instrument_json_destination_name") or DEFAULT_DEST_NAME)

    try:
        session_dir = _resolve_session_dir(params)
    except Exception as exc:  # noqa: BLE001
        LOG.error("instrument_json_fetch: unable to resolve session folder: %s", exc)
        return 1

    dest_path = session_dir / dest_name

    explicit_source = _resolve_explicit_source_path(params)
    if explicit_source is not None:
        candidate = explicit_source
    else:
        root = _resolve_source_root(params)
        candidate = _find_latest_instrument_json(root, filename=filename, recursive=recursive)

    if candidate is None or not candidate.exists() or not candidate.is_file():
        msg = "instrument_json_fetch: no instrument.json found"
        if explicit_source:
            msg += f" at {explicit_source}"
        else:
            msg += f" under {str(_resolve_source_root(params))}"

        if not assume_yes:
            print(msg + ".")
            alternate = _prompt_for_alternate_path(assume_yes=assume_yes)
            if alternate is not None:
                candidate = alternate

        if candidate is None or not candidate.exists() or not candidate.is_file():
            if required:
                LOG.error(msg)
                return 1
            LOG.warning(msg + "; continuing")
            return 0

    chosen_mtime = _format_mtime(candidate)
    LOG.info("instrument_json_fetch: candidate=%s (modified=%s)", candidate, chosen_mtime)

    if not _prompt_yes_no(
        f"Use instrument.json from '{candidate}' (modified {chosen_mtime})?",
        default_yes=True,
        assume_yes=assume_yes,
    ):
        alternate = _prompt_for_alternate_path(assume_yes=assume_yes)
        if alternate is None:
            if required:
                LOG.error("instrument_json_fetch: operator declined instrument.json and did not provide an alternate")
                return 1
            LOG.warning("instrument_json_fetch: operator declined instrument.json; continuing")
            return 0
        candidate = alternate
        chosen_mtime = _format_mtime(candidate)
        LOG.info("instrument_json_fetch: operator override candidate=%s (modified=%s)", candidate, chosen_mtime)

    if dest_path.exists():
        if not _prompt_yes_no(
            f"'{dest_path.name}' already exists in the session folder. Overwrite?",
            default_yes=True,
            assume_yes=assume_yes,
        ):
            LOG.info("instrument_json_fetch: keeping existing %s", dest_path)
            return 0

    try:
        shutil.copy2(candidate, dest_path)
    except Exception as exc:  # noqa: BLE001
        LOG.error("instrument_json_fetch: failed to copy '%s' -> '%s': %s", candidate, dest_path, exc, exc_info=True)
        return 1

    LOG.info("instrument_json_fetch: copied %s -> %s", candidate, dest_path)
    return 0
