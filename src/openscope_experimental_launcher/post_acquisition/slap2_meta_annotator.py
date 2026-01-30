"""Annotate and normalize SLAP2 session files before archiving.

Steps:
- Prompt operator once for shared brain area and DMD1/DMD2 depths (no per-file prompts).
- Discover .meta files, classify type, prompt to confirm per file.
- Rename stems to a normalized form, move meta + sibling files into
    convention subfolders, and emit per-stem annotations and a routing
    manifest for the archiver.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from openscope_experimental_launcher.utils import param_utils
from openscope_experimental_launcher.utils import manifest_utils

LOG = logging.getLogger(__name__)


TYPE_DYNAMIC = "dynamic"
TYPE_STRUCTURE = "structure"
TYPE_REFSTACK = "ref_stack"
TYPE_UNKNOWN = "unknown"


def _prompt(message: str, default: str | None = None, *, assume_yes: bool = False) -> str:
    if assume_yes:
        return default or ""
    prompt = f"{message}"
    if default is not None:
        prompt += f" [{default}]"
    prompt += ": "
    try:
        value = input(prompt)
    except Exception:
        return default or ""
    value = value.strip()
    if not value and default is not None:
        return default
    return value


def _infer_type(stem_lower: str) -> str:
    if stem_lower.startswith("acquisition_"):
        return TYPE_DYNAMIC
    if stem_lower.startswith("structure_"):
        return TYPE_STRUCTURE
    if stem_lower.startswith("refstack_"):
        return TYPE_REFSTACK
    return TYPE_UNKNOWN


def _collect_siblings(meta_path: Path) -> List[Path]:
    stem = meta_path.stem
    return list(meta_path.parent.glob(f"{stem}*"))


def _build_normalized_stem(file_type: str, original_stem: str, counter: int) -> str:
    """Normalize stem without counters, using SLAP2 prefixes.

    dynamic -> acquisition_
    structure -> structure_
    ref_stack -> refStack_
    """
    base = original_stem.replace(" ", "_")
    prefix_map = {
        TYPE_DYNAMIC: "acquisition",
        TYPE_STRUCTURE: "structure",
        TYPE_REFSTACK: "refStack",
    }
    prefix = prefix_map.get(file_type, file_type)
    return f"{prefix}_{base}"


def _write_annotation(annotation_path: Path, payload: Dict[str, Any]) -> None:
    annotation_path.parent.mkdir(parents=True, exist_ok=True)
    annotation_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
def _collect_launcher_metadata(session_dir: Path) -> List[str]:
    metadata_dir = session_dir / "launcher_metadata"
    if not metadata_dir.exists():
        return []
    return [p.relative_to(session_dir).as_posix() for p in metadata_dir.rglob("*") if p.is_file()]


def run(params: Dict[str, Any]) -> int:
    if params is None:
        params = {}
    elif not isinstance(params, dict):
        LOG.warning("slap2_meta_annotator received non-dict params; interpreting as manifest_path")
        params = {"manifest_path": params}

    # Defaults and parameters
    session_dir_param = params.get("output_session_folder")
    if not session_dir_param:
        LOG.error("output_session_folder is required for slap2_meta_annotator")
        return 2
    session_dir = Path(str(session_dir_param)).expanduser().resolve()

    assume_yes = bool(params.get("assume_yes", False))
    default_brain_area = str(params.get("default_brain_area", "VISp"))
    dynamic_dir = params.get("dynamic_dir", "dynamic_data")
    structure_dir = params.get("structure_dir", "static_data")
    ref_stack_dir = params.get("ref_stack_dir", "dynamic_data/reference_stack")
    manifest_name = params.get("manifest_name", "routing_manifest.json")

    manifest_path_param = params.get("manifest_path")
    if manifest_path_param:
        manifest_path_obj = Path(str(manifest_path_param)).expanduser()
        routing_manifest_path = (
            manifest_path_obj if manifest_path_obj.is_absolute() else session_dir / manifest_path_obj
        )
    else:
        routing_manifest_path = session_dir / "launcher_metadata" / manifest_name

    LOG.info("SLAP2 meta annotator starting | session_dir=%s", session_dir)

    if not session_dir.exists():
        LOG.error("Session directory does not exist: %s", session_dir)
        return 2

    # Session-level defaults (prompt once)
    brain_area_default = _prompt(
        "Default brain area for meta files? (used as per-file default)",
        default_brain_area,
        assume_yes=assume_yes,
    )

    entries: List[Dict[str, Any]] = manifest_utils.read_manifest_entries(routing_manifest_path)
    counter = 1

    meta_files = sorted(session_dir.rglob("*.meta"))
    if not meta_files:
        LOG.warning("No .meta files found under %s", session_dir)
        return 0

    for meta_path in meta_files:
        stem_lower = meta_path.stem.lower()
        inferred_type = _infer_type(stem_lower)
        type_default = {
            TYPE_DYNAMIC: "1",
            TYPE_STRUCTURE: "2",
            TYPE_REFSTACK: "3",
        }.get(inferred_type, "1")
        type_choice_raw = _prompt(
            f"Classify meta '{meta_path.relative_to(session_dir)}' (1=dynamic, 2=structure, 3=ref_stack, 4=skip)",
            type_default,
            assume_yes=assume_yes,
        ).strip().lower()

        choice_map = {
            "1": TYPE_DYNAMIC,
            "2": TYPE_STRUCTURE,
            "3": TYPE_REFSTACK,
            "4": "skip",
        }
        type_choice = choice_map.get(type_choice_raw, TYPE_DYNAMIC)

        if type_choice == "skip":
            LOG.info("Skipping meta file: %s", meta_path)
            continue
        if type_choice not in {TYPE_DYNAMIC, TYPE_STRUCTURE, TYPE_REFSTACK}:
            LOG.warning("Unknown type for %s; skipping", meta_path)
            continue

        device = None
        if "dmd1" in stem_lower:
            device = "dmd1"
        elif "dmd2" in stem_lower:
            device = "dmd2"

        depth_prompt = f"Depth for {device.upper()} (microns from brain surface)?" if device else "Depth for meta (microns from brain surface)?"
        depth_value = _prompt(depth_prompt, None, assume_yes=assume_yes)

        brain_area_value = _prompt(
            f"Brain area for meta '{meta_path.relative_to(session_dir)}'?",
            brain_area_default,
            assume_yes=assume_yes,
        )

        normalized_stem = _build_normalized_stem(type_choice, meta_path.stem, counter)
        counter += 1

        if type_choice == TYPE_DYNAMIC:
            dest_rel_dir = dynamic_dir
        elif type_choice == TYPE_STRUCTURE:
            dest_rel_dir = structure_dir
        else:
            dest_rel_dir = ref_stack_dir

        dest_dir = session_dir / dest_rel_dir
        dest_dir.mkdir(parents=True, exist_ok=True)

        siblings = _collect_siblings(meta_path)
        planned: List[Tuple[Path, Path]] = []
        for src in siblings:
            rel_name = src.name.replace(meta_path.stem, normalized_stem, 1)
            planned.append((src, dest_dir / rel_name))

        LOG.info("Planned moves for %s -> %s", meta_path.stem, dest_rel_dir)
        for src, dst in planned:
            LOG.info("  %s -> %s", src.relative_to(session_dir), dst.relative_to(session_dir))

        proceed = True
        if not assume_yes:
            confirm = _prompt("Apply these moves? (y/N)", "y", assume_yes=assume_yes).lower()
            proceed = confirm in {"y", "yes"}

        if not proceed:
            LOG.info("Operator declined moves for %s; skipping", meta_path)
            continue

        moved_files: List[str] = []
        for src, dst in planned:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                dst = dst.with_name(dst.stem + "_dup" + dst.suffix)
            shutil.move(str(src), dst)
            moved_files.append(dst.relative_to(session_dir).as_posix())

        annotation_path = dest_dir / f"{normalized_stem}.annotation.json"
        annotation_payload = {
            "original_stem": meta_path.stem,
            "normalized_stem": normalized_stem,
            "type": type_choice,
            "depth": depth_value,
            "brain_area": brain_area_value,
            "operator": params.get("user_id") or params.get("operator"),
            "moved_files": moved_files,
            "source_rel": meta_path.relative_to(session_dir).as_posix(),
            "dest_dir": dest_rel_dir,
        }
        _write_annotation(annotation_path, annotation_payload)

        annotation_rel = annotation_path.relative_to(session_dir).as_posix()
        moved_with_annotation = moved_files + [annotation_rel]

        entries.append(
            {
                "source": meta_path.relative_to(session_dir).as_posix(),
                "dest_rel": dest_rel_dir,
                "normalized_stem": normalized_stem,
                "type": type_choice,
                "depth": depth_value,
                "brain_area": brain_area_value,
                "files": moved_with_annotation,
            }
        )

    launcher_metadata_files = _collect_launcher_metadata(session_dir)
    if launcher_metadata_files:
        existing_metadata = next((e for e in entries if e.get("type") == "launcher_metadata"), None)
        if existing_metadata:
            file_set = set(existing_metadata.get("files", []) or [])
            file_set.update(launcher_metadata_files)
            existing_metadata["files"] = sorted(file_set)
        else:
            entries.append({"type": "launcher_metadata", "files": sorted(set(launcher_metadata_files))})

    # Ensure slap2_machine.json is archived
    machine_path = session_dir / "slap2_machine.json"
    if machine_path.exists():
        rel = machine_path.relative_to(session_dir).as_posix()
        existing_machine = next((e for e in entries if e.get("type") == "slap2_machine"), None)
        if existing_machine:
            files = set(existing_machine.get("files", []) or [])
            files.add(rel)
            existing_machine["files"] = sorted(files)
        else:
            entries.append({"type": "slap2_machine", "files": [rel]})

    if entries:
        manifest_utils.write_manifest(routing_manifest_path, entries)
        LOG.info("Routing manifest written: %s", routing_manifest_path)

    return 0
def run_post_acquisition(param_file: Union[str, Dict[str, Any]], overrides: Optional[Dict[str, Any]] = None) -> int:
    try:
        params = param_utils.load_parameters(param_file=param_file, overrides=overrides)
        return run(params)
    except Exception as exc:  # noqa: BLE001
        LOG.error("SLAP2 meta annotation failed: %s", exc, exc_info=True)
        return 1
