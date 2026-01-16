"""Collect and organize SLAP2 stimuli CSV files for archiving.

- Prompts operator to choose which .harp folder (behavior session) to use.
- Moves all CSVs (including orientations_*.csv) into behavior/stimuli/ (or stimuli/ if no behavior root).
- Ensures predictive_processing_session.csv is present in stimuli/ (copied if found elsewhere).
- Registers all moved/copied CSVs in the routing manifest so the archiver copies them.
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from openscope_experimental_launcher.utils import manifest_utils, param_utils

LOG = logging.getLogger(__name__)


def _prompt(message: str, default: str | None, assume_yes: bool) -> str:
    if assume_yes:
        return default or ""
    try:
        return param_utils.get_user_input(message, default)
    except Exception:
        return default or ""


def _list_harp_dirs(session_dir: Path) -> List[Path]:
    return [p for p in session_dir.rglob("*.harp") if p.is_dir()]


def _dir_size_bytes(path: Path) -> int:
    total = 0
    for file_path in path.rglob("*"):
        if not file_path.is_file():
            continue
        try:
            total += file_path.stat().st_size
        except OSError:
            continue
    return total


def _format_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{int(num_bytes)} B"


def _pick_harp_dir(harp_dirs: List[Path], prompt_on_multiple: bool = True) -> Path | None:
    if not harp_dirs:
        return None
    harp_dirs_sorted = sorted(harp_dirs, key=lambda p: p.stat().st_mtime, reverse=True)
    default_dir = harp_dirs_sorted[0]
    if len(harp_dirs_sorted) == 1 or not prompt_on_multiple:
        return default_dir

    option_lines = []
    for i, path in enumerate(harp_dirs_sorted):
        try:
            size_str = _format_size(_dir_size_bytes(path))
        except Exception as exc:  # noqa: BLE001
            LOG.warning("Failed to compute size for %s: %s", path, exc)
            size_str = "size unavailable"
        option_lines.append(f"[{i}] {path} ({size_str})")
    options = "\n".join(option_lines)
    choice_raw = _prompt(
        f"Select .harp folder (default 0 = newest):\n{options}",
        "0",
        assume_yes=False,
    )
    try:
        idx = int(choice_raw)
        if 0 <= idx < len(harp_dirs_sorted):
            return harp_dirs_sorted[idx]
    except ValueError:
        pass
    return default_dir


def run(params: Dict[str, Any]) -> int:
    if params is None:
        params = {}
    elif not isinstance(params, dict):
        LOG.warning("slap2_stimuli_p3_annotator received non-dict params; interpreting as session dir")
        params = {"output_session_folder": params}

    session_dir_param = params.get("output_session_folder")
    if not session_dir_param:
        LOG.error("output_session_folder is required for slap2_stimuli_p3_annotator")
        return 2
    session_dir = Path(str(session_dir_param)).expanduser().resolve()

    prompt_on_multiple = bool(params.get("prompt_on_multiple", True))
    manifest_name = params.get("manifest_name", "routing_manifest.json")

    behavior_root_param = params.get("behavior_root")
    if behavior_root_param:
        behavior_root = Path(str(behavior_root_param)).expanduser()
        if not behavior_root.is_absolute():
            behavior_root = session_dir / behavior_root
    else:
        behavior_root = session_dir / "behavior"
    if not behavior_root.exists():
        behavior_root = session_dir

    manifest_path_param = params.get("manifest_path")
    if manifest_path_param:
        manifest_path_obj = Path(str(manifest_path_param)).expanduser()
        routing_manifest_path = (
            manifest_path_obj if manifest_path_obj.is_absolute() else session_dir / manifest_path_obj
        )
    else:
        routing_manifest_path = session_dir / "launcher_metadata" / manifest_name

    if not session_dir.exists():
        LOG.error("Session directory does not exist: %s", session_dir)
        return 2

    harp_dirs = _list_harp_dirs(session_dir)
    if not harp_dirs:
        LOG.warning("No .harp folders found under %s", session_dir)
        return 0

    chosen_dir = _pick_harp_dir(harp_dirs, prompt_on_multiple=prompt_on_multiple)
    if chosen_dir is None:
        LOG.warning("No .harp folder selected")
        return 0

    parent_dir = chosen_dir.parent
    stimuli_dir = behavior_root / "stimuli"

    def _is_stimulus_csv(path: Path) -> bool:
        name = path.name.lower()
        return name.startswith("orientations_") or name == "predictive_processing_session.csv"

    csv_paths = []
    search_roots = {parent_dir, session_dir}
    for search_dir in search_roots:
        csv_paths.extend(p for p in search_dir.glob("*.csv") if _is_stimulus_csv(p))

    # Also search deeper (e.g., the original Bonsai output folder) for stimulus CSVs.
    for p in session_dir.rglob("*.csv"):
        if _is_stimulus_csv(p):
            csv_paths.append(p)

    # Deduplicate while preserving path objects
    csv_paths = list({p.resolve(): p for p in csv_paths}.values())

    if not csv_paths:
        LOG.info("No stimuli CSV files found near harp or session root: %s | %s", parent_dir, session_dir)
        return 0

    LOG.info("Found %d stimulus CSV(s): %s", len(csv_paths), [p.relative_to(session_dir).as_posix() for p in csv_paths])
    stimuli_paths: List[Path] = []
    stimuli_dir.mkdir(parents=True, exist_ok=True)

    for csv_path in csv_paths:
        dest = stimuli_dir / csv_path.name
        if dest == csv_path:
            stimuli_paths.append(dest)
            continue
        if dest.exists():
            dest = dest.with_name(dest.stem + "_dup" + dest.suffix)
        try:
            shutil.move(str(csv_path), dest)
            LOG.info("Moved stimuli CSV %s -> %s", csv_path, dest)
        except Exception as exc:  # noqa: BLE001
            LOG.warning("Move failed for %s -> %s (%s); attempting copy then delete", csv_path, dest, exc)
            try:
                shutil.copy2(csv_path, dest)
                csv_path.unlink(missing_ok=True)
                LOG.info("Copied stimuli CSV %s -> %s", csv_path, dest)
            except Exception as exc_copy:  # noqa: BLE001
                LOG.error("Failed to move or copy stimuli CSV %s -> %s: %s", csv_path, dest, exc_copy)
                continue
        stimuli_paths.append(dest)

    if not any(p.name == "predictive_processing_session.csv" for p in stimuli_paths):
        extra_predictive = list(session_dir.rglob("predictive_processing_session.csv"))
        if extra_predictive:
            src = extra_predictive[0]
            stimuli_dir.mkdir(parents=True, exist_ok=True)
            dest = stimuli_dir / src.name
            if dest.exists():
                dest = dest.with_name(dest.stem + "_dup" + dest.suffix)
            try:
                shutil.copy2(src, dest)
                stimuli_paths.append(dest)
            except Exception as exc:  # noqa: BLE001
                LOG.warning("Failed to copy predictive_processing_session.csv to stimuli folder: %s", exc)

    files_for_manifest = sorted({p.relative_to(session_dir).as_posix() for p in stimuli_paths})

    if not files_for_manifest:
        LOG.info("No stimuli CSV files found to register")
        return 0

    entries: List[Dict[str, Any]] = manifest_utils.read_manifest_entries(routing_manifest_path)
    entries.append({"type": "stimuli", "files": files_for_manifest})

    manifest_utils.write_manifest(routing_manifest_path, entries)
    LOG.info("Stimuli manifest written: %s", routing_manifest_path)

    return 0


def run_post_acquisition(param_file: Union[str, Dict[str, Any]], overrides: Optional[Dict[str, Any]] = None) -> int:
    try:
        if isinstance(param_file, dict):
            params = dict(param_file)
            if overrides:
                params.update(overrides)
        else:
            params = param_utils.load_parameters(param_file=param_file, overrides=overrides)
        return run(params)
    except Exception as exc:  # noqa: BLE001
        LOG.error("Stimuli annotation failed: %s", exc, exc_info=True)
        return 1
