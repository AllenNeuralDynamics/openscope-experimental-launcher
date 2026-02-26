"""Pre-acquisition disk space guard.

This module checks free disk space on the volume hosting the session folder and
fails pre-acquisition if the available space is below a configured threshold.

Typical configuration (in a param pack):

    {
      "module_type": "launcher_module",
      "module_path": "disk_space_check",
      "module_parameters": {
        "required_free_gb": 250
      }
    }

"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class DiskUsage:
    total_bytes: int
    used_bytes: int
    free_bytes: int


def _format_gb(num_bytes: int) -> str:
    gb = num_bytes / (1024**3)
    return f"{gb:,.2f} GB"


def _resolve_check_path(params: Mapping[str, Any]) -> Path:
    raw = params.get("disk_space_check_path") or params.get("output_session_folder")
    if not raw:
        raise ValueError("disk_space_check_path or output_session_folder is required")
    # Avoid Path.resolve() which can be slow/problematic on some UNC paths.
    return Path(str(raw)).expanduser()


def _read_required_free_bytes(params: Mapping[str, Any]) -> int:
    if params.get("required_free_gb") is None:
        raise ValueError("required_free_gb must be provided")

    try:
        required_gb = float(params.get("required_free_gb"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"required_free_gb must be a number: {exc}") from exc

    if required_gb <= 0:
        raise ValueError("required_free_gb must be > 0")

    return int(required_gb * (1024**3))


def _prompt(message: str) -> str:
    try:
        return input(message)
    except (EOFError, OSError):
        return ""


def _prompt_yes_no(
    message: str,
    *,
    default_yes: bool = False,
) -> bool:
    """Prompt yes/no.
    """

    suffix = "(Y/n)" if default_yes else "(y/N)"
    while True:
        raw = _prompt(f"{message} {suffix}: ").strip().lower()
        if not raw:
            # If stdin unavailable, _prompt returns ""; distinguish from user Enter.
            # We can't tell the difference reliably, so treat empty as default.
            # Callers that want strict non-interactive behavior should set allow_override=False.
            return default_yes
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("Please enter y or n.")


def _get_disk_usage(path: Path) -> DiskUsage:
    usage = shutil.disk_usage(os.fspath(path))
    return DiskUsage(total_bytes=int(usage.total), used_bytes=int(usage.used), free_bytes=int(usage.free))


def run_pre_acquisition(params: Mapping[str, Any]) -> int:
    """Validate minimum free disk space before starting acquisition.

    Module parameters (set via `module_parameters`):
    - `required_free_gb` (float, required): Minimum free space required (GiB).
    - `disk_space_check_path` (str, optional): Path to check; defaults to `output_session_folder`.
    - `allow_override` (bool, default False): If True, prompt operator to continue anyway.

    Returns:
        int: 0 if sufficient space (or overridden); 1 otherwise.
    """

    try:
        check_path = _resolve_check_path(params)
        required_free_bytes = _read_required_free_bytes(params)
    except Exception as exc:  # noqa: BLE001
        LOG.error("disk_space_check: invalid configuration: %s", exc)
        return 1

    allow_override = bool(params.get("allow_override", False))

    try:
        usage = _get_disk_usage(check_path)
    except Exception as exc:  # noqa: BLE001
        LOG.error("disk_space_check: failed to read disk usage for '%s': %s", check_path, exc)
        return 1

    LOG.info(
        "disk_space_check: path=%s free=%s required=%s total=%s",
        os.fspath(check_path),
        _format_gb(usage.free_bytes),
        _format_gb(required_free_bytes),
        _format_gb(usage.total_bytes),
    )

    if usage.free_bytes >= required_free_bytes:
        return 0

    msg = (
        f"Insufficient free disk space for session folder volume. "
        f"Free: {_format_gb(usage.free_bytes)}; "
        f"Required: {_format_gb(required_free_bytes)}; "
        f"Path: {check_path}"
    )

    if not allow_override:
        LOG.error("disk_space_check: %s", msg)
        return 1

    LOG.warning("disk_space_check: %s", msg)
    ok = _prompt_yes_no("Continue anyway?", default_yes=False)
    if ok:
        LOG.warning("disk_space_check: operator override accepted; proceeding")
        return 0

    LOG.error("disk_space_check: operator declined override; aborting")
    return 1
