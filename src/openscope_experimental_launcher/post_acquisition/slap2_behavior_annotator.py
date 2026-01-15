"""Normalize Bonsai Harp outputs into AIND harp format for SLAP2 behavior.

- Discover *.harp folders under the session.
- If multiple, default to the most recently modified; prompt operator to choose/confirm.
- Move the chosen harp folder to the session root as <Device>.harp (default device VCO1_Behavior).
- Rename contained files to include the device prefix and update YAML content to the device.
- Append entries to the routing manifest so the archiver can route these files.
"""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from openscope_experimental_launcher.utils import param_utils
from openscope_experimental_launcher.utils import manifest_utils

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


def _pick_harp_dir(harp_dirs: List[Path], assume_yes: bool) -> Path | None:
    if not harp_dirs:
        return None
    harp_dirs_sorted = sorted(harp_dirs, key=lambda p: p.stat().st_mtime, reverse=True)
    default_dir = harp_dirs_sorted[0]
    if len(harp_dirs_sorted) == 1 or assume_yes:
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


def _rename_files(target_dir: Path, old_stem: str, device_name: str) -> List[Path]:
    renamed: List[Path] = []
    for path in list(target_dir.iterdir()):
        if not path.is_file():
            continue
        old_base = path.stem
        suffix = "".join(path.suffixes)
        new_base = old_base
        if old_stem and old_base.startswith(old_stem):
            new_base = device_name + old_base[len(old_stem) :]
        elif not old_base.startswith(device_name):
            new_base = f"{device_name}_{old_base}"

        behavior_prefix = f"{device_name}_Behavior"
        if new_base.startswith(behavior_prefix):
            remainder = new_base[len(behavior_prefix) :]
            if remainder.startswith("_"):
                remainder = remainder[1:]
            new_base = f"{device_name}_{remainder}" if remainder else device_name

        dup_device_prefix = f"{device_name}_{device_name}_"
        if new_base.startswith(dup_device_prefix):
            new_base = f"{device_name}_{new_base[len(dup_device_prefix):]}"

        while "__" in new_base:
            new_base = new_base.replace("__", "_")
        new_base = new_base.rstrip("_")

        new_path = path.with_name(new_base + suffix)
        if new_path != path:
            path.rename(new_path)
        renamed.append(new_path)
    return renamed


def _update_yaml_device(file_paths: List[Path], old_stem: str, device_name: str) -> None:
    for path in file_paths:
        if path.suffix.lower() != ".yml":
            continue
        try:
            text = path.read_text(encoding="utf-8")
            if old_stem:
                text = text.replace(old_stem, device_name)
            text = re.sub(r"(?m)^device:\s*.*$", f"device: {device_name}", text)
            path.write_text(text, encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            LOG.warning("Failed to update YAML device in %s: %s", path, exc)


def _next_available_dir(base_dir: Path, desired_name: str, current_path: Path) -> Path:
    target = base_dir / desired_name
    if target == current_path:
        return target
    if not target.exists():
        return target
    stem = Path(desired_name).stem
    suffix = Path(desired_name).suffix
    counter = 2
    while True:
        candidate = base_dir / f"{stem}_{counter}{suffix}"
        if candidate == current_path or not candidate.exists():
            return candidate
        counter += 1


def _collect_launcher_metadata(session_dir: Path) -> List[str]:
    metadata_dir = session_dir / "launcher_metadata"
    if not metadata_dir.exists():
        return []
    return [p.relative_to(session_dir).as_posix() for p in metadata_dir.rglob("*") if p.is_file()]


def run(params: Dict[str, Any]) -> int:
    if params is None:
        params = {}
    elif not isinstance(params, dict):
        LOG.warning("slap2_behavior_annotator received non-dict params; interpreting as session dir")
        params = {"output_session_folder": params}

    session_dir_param = params.get("output_session_folder")
    if not session_dir_param:
        LOG.error("output_session_folder is required for slap2_behavior_annotator")
        return 2
    session_dir = Path(str(session_dir_param)).expanduser().resolve()

    assume_yes = bool(params.get("assume_yes", False))
    device_name = str(params.get("device_name", "VCO1_Behavior"))
    manifest_name = params.get("manifest_name", "routing_manifest.json")

    behavior_root_param = params.get("behavior_root")
    if behavior_root_param:
        behavior_root = Path(str(behavior_root_param)).expanduser()
        if not behavior_root.is_absolute():
            behavior_root = session_dir / behavior_root
    else:
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

    chosen_dir = _pick_harp_dir(harp_dirs, assume_yes=assume_yes)
    if chosen_dir is None:
        LOG.warning("No .harp folder selected")
        return 0

    if not assume_yes:
        confirm = _prompt(f"Use harp folder '{chosen_dir}'? (y/N)", "n", assume_yes=False)
        if str(confirm).lower() not in {"y", "yes"}:
            LOG.info("Operator declined harp folder selection")
            return 0

    old_stem = chosen_dir.stem
    target_name = f"{device_name}.harp"
    final_harp_dir = _next_available_dir(behavior_root, target_name, chosen_dir)
    if final_harp_dir != chosen_dir:
        final_harp_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(chosen_dir), final_harp_dir)
    else:
        final_harp_dir = chosen_dir

    renamed_files = _rename_files(final_harp_dir, old_stem=old_stem, device_name=device_name)
    _update_yaml_device(renamed_files, old_stem=old_stem, device_name=device_name)

    file_list = [p.relative_to(session_dir).as_posix() for p in final_harp_dir.glob("*") if p.is_file()]

    entries: List[Dict[str, Any]] = manifest_utils.read_manifest_entries(routing_manifest_path)

    entries.append(
        {
            "type": "behavior_harp",
            "device": device_name,
            "harp_dir": final_harp_dir.relative_to(session_dir).as_posix(),
            "files": file_list,
        }
    )

    metadata_files = _collect_launcher_metadata(session_dir)
    if metadata_files:
        existing_metadata = next((e for e in entries if e.get("type") == "launcher_metadata"), None)
        if existing_metadata:
            merged = set(existing_metadata.get("files", []) or [])
            merged.update(metadata_files)
            existing_metadata["files"] = sorted(merged)
        else:
            entries.append({"type": "launcher_metadata", "files": sorted(set(metadata_files))})

    manifest_utils.write_manifest(routing_manifest_path, entries)
    LOG.info("Behavior harp manifest written: %s", routing_manifest_path)

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
        LOG.error("Behavior harp annotation failed: %s", exc, exc_info=True)
        return 1
