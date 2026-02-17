"""Annotate and normalize SLAP2 session files before archiving.

Steps:
- Prompt operator for shared experiment-level annotations (asked once per run).
- Prompt operator for DMD-level defaults (e.g. pia depth on remote focus) and
    allow per-file overrides.
- Discover .meta files, classify type, prompt to confirm per file.
- Rename stems to a normalized form, move meta + sibling files into
    convention subfolders, and emit per-stem annotations and a routing
    manifest for the archiver.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import requests

from openscope_experimental_launcher.utils import param_utils
from openscope_experimental_launcher.utils import manifest_utils

LOG = logging.getLogger(__name__)


TYPE_DYNAMIC = "dynamic"
TYPE_STRUCTURE = "structure"
TYPE_REFSTACK = "ref_stack"
TYPE_UNKNOWN = "unknown"


GREEN_CHANNEL_TARGETS = (
    "iGluSnFR4s",
    "iGluSnFR4f",
    "iGluSnFR3",
    "GFP",
    "FORCEB",
    "ASAP7y",
)

RED_CHANNEL_TARGETS = (
    "jRGECO1a",
    "RCaMP2",
    "RCaMP3",
    "VADER",
)

SLAP2_MODES = (
    "full-field raster",
    "multi-roi raster",
    "band scan",
    "integration scan",
)


TARGET_NAME_RE = re.compile(r"^(Neuron|FOV)(\d+)$", re.IGNORECASE)


def _parse_target_name(value: str | None) -> tuple[str | None, int | None]:
    if not value:
        return None, None
    match = TARGET_NAME_RE.match(str(value).strip())
    if not match:
        return None, None
    kind, number = match.groups()
    try:
        return kind.upper(), int(number)
    except Exception:  # noqa: BLE001
        return None, None


def _prompt_float(
    message: str,
    default: float | None = None,
    *,
    assume_yes: bool = False,
) -> float | None:
    if assume_yes:
        return default

    default_str = None if default is None else str(default)
    while True:
        raw = _prompt(message, default_str, assume_yes=assume_yes).strip()
        if not raw:
            return default
        try:
            return float(raw)
        except ValueError:
            print("Invalid number. Please enter a value in microns (e.g. 150).")


def _prompt_target_name(
    message: str,
    default: str | None = None,
    *,
    assume_yes: bool = False,
) -> str:
    if assume_yes:
        return default or ""

    default_kind, default_number = _parse_target_name(default)
    kind_default = "FOV" if default_kind is None else default_kind
    number_default = "1" if default_number is None else str(default_number)

    while True:
        kind_raw = _prompt(
            f"{message} type? (FOV or Neuron)",
            kind_default,
            assume_yes=assume_yes,
        ).strip()
        if not kind_raw:
            kind_raw = kind_default

        kind = kind_raw.strip().upper()
        if kind not in {"FOV", "NEURON"}:
            print("Invalid type. Choose 'FOV' or 'Neuron'.")
            continue

        number_raw = _prompt(
            f"{message} number?",
            number_default,
            assume_yes=assume_yes,
        ).strip()
        if not number_raw:
            number_raw = number_default

        if not number_raw.isdigit() or int(number_raw) <= 0:
            print("Invalid number. Enter a positive integer (e.g. 1, 2, 3).")
            continue

        prefix = "FOV" if kind == "FOV" else "Neuron"
        return f"{prefix}{int(number_raw)}"


def _ccf_acronym_exists(acronym: str, *, timeout_s: float = 1.0) -> bool:
    """Validate an Allen CCF structure acronym via the Allen Brain Map API.

    If the API is unreachable, this function raises (callers should handle and
    fall back to permissive behavior).
    """

    # Allen Brain Map API (public). Use acronym exact match.
    url = "https://api.brain-map.org/api/v2/data/Structure/query.json"
    criteria = f"[acronym$eq'{acronym}']"
    # Use explicit (connect, read) timeouts to reduce the risk of hanging in
    # restricted/offline lab environments.
    response = requests.get(url, params={"criteria": criteria}, timeout=(timeout_s, timeout_s))
    response.raise_for_status()
    payload = response.json()
    return int(payload.get("total_rows", 0)) > 0


def _fetch_structures_graph1(*, timeout_s: float = 2.0) -> List[Dict[str, str]]:
    """Fetch Structure rows for the default mouse CCF graph (graph_id=1)."""

    url = "https://api.brain-map.org/api/v2/data/Structure/query.json"
    response = requests.get(
        url,
        params={
            "criteria": "[graph_id$eq1]",
            "only": "acronym,name",
            # total_rows is currently ~1300, so a single page is fine.
            "num_rows": 2000,
        },
        timeout=(timeout_s, timeout_s),
    )
    response.raise_for_status()
    payload = response.json()
    rows = payload.get("msg")
    if not isinstance(rows, list):
        raise ValueError("Unexpected Structure query response")
    out: List[Dict[str, str]] = []
    for row in rows:
        acronym = row.get("acronym")
        name = row.get("name")
        if isinstance(acronym, str) and isinstance(name, str):
            out.append({"acronym": acronym, "name": name})
    return out


def _get_visual_cortex_structures(*, timeout_s: float = 2.0) -> List[Dict[str, str]]:
    """Return a list of VIS* structures (excluding VISC* visceral area)."""

    rows = _fetch_structures_graph1(timeout_s=timeout_s)
    vis_rows = [
        r
        for r in rows
        if r["acronym"].startswith("VIS") and not r["acronym"].startswith("VISC")
    ]
    return sorted(vis_rows, key=lambda r: r["acronym"])


def _prompt_targeted_structure(
    message: str,
    default: str | None = None,
    *,
    assume_yes: bool = False,
    validate_ccf: bool = True,
    cache: Dict[str, bool] | None = None,
) -> str:
    if assume_yes:
        return default or ""

    if cache is None:
        cache = {}

    visual_cortex_choices: List[Dict[str, str]] | None = None

    while True:
        raw = _prompt(message, default, assume_yes=assume_yes).strip()
        if not raw:
            raw = default or ""

        if not validate_ccf:
            return raw

        key = raw.strip()
        if key in cache:
            if cache[key]:
                return raw
            print("Not a valid Allen CCF structure acronym. Try e.g. 'VISp'.")
            continue

        try:
            ok = _ccf_acronym_exists(key)
        except Exception as exc:  # noqa: BLE001
            LOG.warning(
                "Unable to validate targeted structure against Allen CCF (continuing without validation): %s",
                exc,
            )
            return raw

        cache[key] = ok
        if ok:
            return raw

        print("Not a valid Allen CCF structure acronym. Try e.g. 'VISp'.")
        try:
            if visual_cortex_choices is None:
                visual_cortex_choices = _get_visual_cortex_structures(timeout_s=2.0)
            if visual_cortex_choices:
                print("Common VIS (visual cortex) acronyms include:")
                for row in visual_cortex_choices[:40]:
                    print(f"  {row['acronym']}: {row['name']}")
                if len(visual_cortex_choices) > 40:
                    print(f"  ... ({len(visual_cortex_choices)} total VIS* entries)")
        except Exception as exc:  # noqa: BLE001
            LOG.debug("Unable to fetch VIS structure suggestions: %s", exc)


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


def _prompt_choice(
    message: str,
    choices: Tuple[str, ...],
    *,
    default: str | None = None,
    assume_yes: bool = False,
) -> str:
    if assume_yes:
        return default or ""

    choice_lines = [f"{idx + 1}) {value}" for idx, value in enumerate(choices)]
    prompt_message = f"{message}\n" + "\n".join(choice_lines)

    default_index = None
    if default and default in choices:
        default_index = str(choices.index(default) + 1)

    while True:
        raw = _prompt(f"{prompt_message}\nSelect one", default_index, assume_yes=assume_yes).strip()
        if not raw and default:
            return default
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        # Allow typing the value directly.
        for value in choices:
            if raw.lower() == value.lower():
                return value
        print("Invalid selection. Please choose a number from the list.")


_DMD_SUFFIX_RE = re.compile(r"([_\- ]dmd[12])$", re.IGNORECASE)


def _meta_group_key(meta_path: Path) -> str:
    """Group meta files so DMD1/DMD2 variants share prompts.

    Many acquisitions generate two files (DMD1/DMD2). We want to prompt once per
    acquisition (per stem without the DMD suffix) and apply to both.
    """

    stem = meta_path.stem
    return _DMD_SUFFIX_RE.sub("", stem)


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
    # For SLAP2 we want deterministic prefixes while retaining the informative suffix.
    # Strip a duplicate prefix if present, drop the first token, then prepend a single prefix.
    doubled = f"{prefix}_"
    base_no_prefix = base[len(doubled):] if base.lower().startswith(doubled.lower()) else base
    base_tail = base_no_prefix.split("_", 1)[1] if "_" in base_no_prefix else base_no_prefix
    return f"{prefix}_{base_tail}"


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
    # Back-compat: allow legacy default_brain_area to populate targeted_structure default.
    default_targeted_structure = params.get("default_targeted_structure")
    if default_targeted_structure is None:
        default_targeted_structure = params.get("default_brain_area", "VISp")

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

    validate_ccf = bool(params.get("validate_targeted_structure_ccf", True))
    ccf_cache: Dict[str, bool] = {}

    # Session-level defaults (prompt once)
    targeted_structure_default = _prompt_targeted_structure(
        "Default Targeted structure? (Allen CCF acronym; used as per-file default)",
        str(default_targeted_structure) if default_targeted_structure else None,
        assume_yes=assume_yes,
        validate_ccf=validate_ccf,
        cache=ccf_cache,
    )

    green_target_default = params.get("default_green_channel_target")
    red_target_default = params.get("default_red_channel_target")

    intended_green_target = _prompt_choice(
        "Question 1: Intended Green Channel Target",
        GREEN_CHANNEL_TARGETS,
        default=str(green_target_default) if green_target_default else None,
        assume_yes=assume_yes,
    )
    intended_red_target = _prompt_choice(
        "Question 2: Intended Red Channel Target",
        RED_CHANNEL_TARGETS,
        default=str(red_target_default) if red_target_default else None,
        assume_yes=assume_yes,
    )

    # Per-acquisition (DMD1/DMD2 pair) prompts.
    modes_by_group: Dict[str, str] = {}

    # Per-DMD defaults (prompted once per DMD) used for per-file pia depth prompt.
    pia_depth_default_by_device: Dict[str, float | None] = {}

    entries: List[Dict[str, Any]] = manifest_utils.read_manifest_entries(routing_manifest_path)
    counter = 1

    meta_files = sorted(session_dir.rglob("*.meta"))
    if not meta_files:
        LOG.warning("No .meta files found under %s", session_dir)
        return 0

    for meta_path in meta_files:
        stem_lower = meta_path.stem.lower()
        group_key = _meta_group_key(meta_path)
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

        if group_key not in modes_by_group:
            default_mode = params.get("default_slap2_mode")
            modes_by_group[group_key] = _prompt_choice(
                f"SLAP2 Modes for '{group_key}' (shared across DMD files)",
                SLAP2_MODES,
                default=str(default_mode) if default_mode else None,
                assume_yes=assume_yes,
            )
        slap2_mode_value = modes_by_group[group_key]

        # Pia depth on remote focus: prompt a DMD-level default once, then allow per-file overrides.
        if device and device not in pia_depth_default_by_device:
            legacy_key = "default_dmd1_depth" if device == "dmd1" else "default_dmd2_depth"
            default_param_key = (
                "default_pia_depth_on_remote_focus_dmd1_um"
                if device == "dmd1"
                else "default_pia_depth_on_remote_focus_dmd2_um"
            )
            default_raw = params.get(default_param_key)
            if default_raw is None:
                default_raw = params.get(legacy_key)

            default_val: float | None = None
            if default_raw not in (None, ""):
                try:
                    default_val = float(default_raw)
                except Exception:  # noqa: BLE001
                    default_val = None

            pia_depth_default_by_device[device] = _prompt_float(
                f"Default Depth of pia on remote focus for {device.upper()} (microns)?",
                default_val,
                assume_yes=assume_yes,
            )

        pia_default = pia_depth_default_by_device.get(device) if device else None
        pia_depth_on_remote_focus_um = _prompt_float(
            f"Depth of pia on remote focus for meta '{meta_path.relative_to(session_dir)}' (microns)?",
            pia_default,
            assume_yes=assume_yes,
        )

        target_name_default = params.get("default_target_name")
        target_name_value = _prompt_target_name(
            f"Target name for meta '{meta_path.relative_to(session_dir)}'? (NeuronX or FOVX)",
            str(target_name_default) if target_name_default else None,
            assume_yes=assume_yes,
        )

        targeted_structure_value = _prompt_targeted_structure(
            f"Targeted structure for meta '{meta_path.relative_to(session_dir)}'? (Allen CCF acronym)",
            targeted_structure_default,
            assume_yes=assume_yes,
            validate_ccf=validate_ccf,
            cache=ccf_cache,
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
            confirm = _prompt("Apply these moves? (Y/n)", "y", assume_yes=assume_yes).lower()
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
            "pia_depth_on_remote_focus_um": pia_depth_on_remote_focus_um,
            "target_name": target_name_value,
            "targeted_structure": targeted_structure_value,
            "intended_green_channel_target": intended_green_target,
            "intended_red_channel_target": intended_red_target,
            "slap2_mode": slap2_mode_value,
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
                "pia_depth_on_remote_focus_um": pia_depth_on_remote_focus_um,
                "target_name": target_name_value,
                "targeted_structure": targeted_structure_value,
                "intended_green_channel_target": intended_green_target,
                "intended_red_channel_target": intended_red_target,
                "slap2_mode": slap2_mode_value,
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
