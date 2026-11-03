"""Annotate and normalize SLAP2 session files before archiving.

Two phases:

Phase A (mechanical, scriptable):
- Close the experiment-notes editor if the notes step left one open.
- Discover .meta files, classify each by content (``enableStack``), stem
  prefix, or an operator prompt; the operator then reviews the full
  classification table before anything moves.
- Rename stems to a normalized form, move meta + sibling files into
  convention subfolders, scaffold per-stem annotation JSONs (prefilled from
  pack params only — this phase asks no metadata questions), and write a
  routing manifest for the archiver.

Phase B (human):
- Open the SLAP2 metadata editor GUI (``slap2_onprem_handling``) on the
  organized session so the operator fills in and confirms the scientific
  metadata. Every GUI problem degrades to a loud warning instead of failing
  the launcher; upload validation blocks incomplete sessions until the
  editor has been run and saved.

Finally the routing manifest is reconciled so files created after the
mechanical pass (editor-written annotations, GIAnT's postacq_annotations.h5,
rig-side extras such as rigDescription.json) are archived too.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from openscope_experimental_launcher.utils import param_utils
from openscope_experimental_launcher.utils import manifest_utils
from openscope_experimental_launcher.utils import notes_editor

LOG = logging.getLogger(__name__)


TYPE_DYNAMIC = "dynamic"
TYPE_STRUCTURE = "structure"
TYPE_REFSTACK = "ref_stack"
TYPE_UNKNOWN = "unknown"

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

    consecutive_blank = 0
    while True:
        raw = _prompt(f"{prompt_message}\nSelect one", default_index, assume_yes=assume_yes).strip()
        if not raw and default:
            return default
        if not raw:
            # _prompt returns "" when stdin is unavailable (EOF/closed): bail
            # out after a few blanks instead of looping forever in headless runs.
            consecutive_blank += 1
            if consecutive_blank >= 3:
                raise RuntimeError(
                    "Operator input required but no input is available "
                    f"(prompt: {message!r}). Run interactively or set assume_yes."
                )
        else:
            consecutive_blank = 0
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


# Built-in stem prefixes per type. The stem prefix is a FREE STRING typed by
# the operator in the SLAP2 software ("acquisition_" is only the default), so
# these sets can never be complete — param packs can extend them via the
# dynamic/structure/ref_stack_stem_prefixes module parameters, and the
# .meta contents (enableStack) are consulted first wherever possible.
_BUILTIN_DYNAMIC_PREFIXES = ("acquisition_", "activity_")
_BUILTIN_STRUCTURE_PREFIXES = ("structure_",)
_BUILTIN_REF_STACK_PREFIXES = ("refstack_",)


def _normalize_prefixes(value: Any, builtin: Tuple[str, ...]) -> Tuple[str, ...]:
    """Combine built-in stem prefixes with pack-declared extras."""
    if not value:
        return builtin
    if isinstance(value, str):
        value = [value]
    extras = tuple(str(v).strip().lower() for v in value if str(v).strip())
    return builtin + extras


def _read_enable_stack(meta_path: Path) -> Optional[bool]:
    """Read the enableStack flag from a SLAP2 .meta file.

    .meta files are MATLAB 7.3 MAT-files, i.e. HDF5, with a top-level
    `enableStack` scalar recording machine truth about whether the
    acquisition was a z-stack (1) or a functional/dynamic acquisition (0).
    Returns True/False, or None when the value cannot be determined (h5py
    unavailable, unreadable file, missing key) — callers then fall back to
    filename-prefix classification.
    """
    try:
        import h5py  # noqa: PLC0415 - degrade gracefully when unavailable
    except ImportError:
        LOG.debug("h5py not available; skipping .meta content classification")
        return None
    try:
        with h5py.File(meta_path, "r") as fh:
            value = fh["enableStack"][()]
        flat = getattr(value, "flat", None)
        scalar = float(flat[0]) if flat is not None else float(value)
        return bool(scalar)
    except Exception as exc:  # noqa: BLE001 - any read issue -> fallback
        LOG.debug("Could not read enableStack from %s: %s", meta_path, exc)
        return None


def _classify_meta(
    meta_path: Path,
    session_dir: Path,
    *,
    dynamic_prefixes: Tuple[str, ...],
    structure_prefixes: Tuple[str, ...],
    ref_stack_prefixes: Tuple[str, ...],
    assume_yes: bool,
    silent_only: bool = False,
) -> Optional[str]:
    """Classify a .meta file as TYPE_DYNAMIC/TYPE_STRUCTURE/TYPE_REFSTACK or "skip".

    Decision ladder:
      1. .meta contents (enableStack): 0 -> dynamic, machine truth, silent.
      2. enableStack == 1 -> a z-stack; the filename prefix picks structure
         vs. reference stack; else ONE contextual two-choice prompt.
      3. Contents unreadable -> filename prefix; unknown names get a
         contextual prompt (no default — invalid input re-prompts rather than
         silently classifying as dynamic).
    With silent_only=True, returns None instead of prompting (callers use
    this to try every member of a DMD pair before asking the operator).
    Files needing a prompt are asked about individually: a shared name prefix
    does not imply a shared type. Under assume_yes, files that would need a
    prompt are skipped loudly: guessing a classification can misfile data.
    """
    rel = meta_path.relative_to(session_dir)
    stem_lower = meta_path.stem.lower()

    def _prefix_type() -> str:
        if stem_lower.startswith(dynamic_prefixes):
            return TYPE_DYNAMIC
        if stem_lower.startswith(structure_prefixes):
            return TYPE_STRUCTURE
        if stem_lower.startswith(ref_stack_prefixes):
            return TYPE_REFSTACK
        return TYPE_UNKNOWN

    enable_stack = _read_enable_stack(meta_path)

    if enable_stack is False:
        LOG.info("Classified %s as dynamic (.meta contents: enableStack=0)", rel)
        return TYPE_DYNAMIC

    if enable_stack is True:
        inferred = _prefix_type()
        if inferred in (TYPE_STRUCTURE, TYPE_REFSTACK):
            LOG.info(
                "Classified %s as %s (.meta contents: z-stack; filename prefix)",
                rel,
                inferred,
            )
            return inferred
        if silent_only:
            return None
        if inferred == TYPE_DYNAMIC:
            LOG.warning(
                "Filename of %s looks dynamic but .meta contents say z-stack; "
                "trusting the contents and asking the operator",
                rel,
            )
        if assume_yes:
            LOG.warning(
                "Cannot classify %s without operator input (z-stack with "
                "unrecognized name) and assume_yes is set; skipping the file",
                rel,
            )
            return "skip"
        selected = _prompt_choice(
            (
                f"\nOperator input needed to classify '{rel}'.\n"
                "The file's contents show it is a z-stack acquisition "
                "(enableStack=1), but its filename does not say which kind of "
                "stack it is. Your answer decides where it is archived:\n"
                "structure stacks go to static_data/ (anatomy), reference "
                "stacks go to dynamic_data/reference_stack/."
            ),
            ("structure stack", "reference stack"),
            assume_yes=assume_yes,
        )
        return TYPE_STRUCTURE if selected == "structure stack" else TYPE_REFSTACK

    # Contents unreadable -> filename prefix fallback.
    inferred = _prefix_type()
    if inferred != TYPE_UNKNOWN:
        LOG.info("Classified %s as %s (filename prefix)", rel, inferred)
        return inferred
    if silent_only:
        return None
    if assume_yes:
        LOG.warning(
            "Cannot classify %s without operator input (contents unreadable, "
            "unrecognized filename) and assume_yes is set; skipping the file",
            rel,
        )
        return "skip"
    selected = _prompt_choice(
        (
            f"\nOperator input needed to classify '{rel}'.\n"
            "The .meta contents could not be read and the filename does not "
            "start with a recognized prefix (acquisition_/activity_/"
            "structure_/refStack_), so the acquisition type is unknown. Your "
            "answer decides where the files are archived and which metadata "
            "they need: dynamic -> dynamic_data/ (functional imaging), "
            "structure stack -> static_data/ (anatomy), reference stack -> "
            "dynamic_data/reference_stack/, or skip to leave the files in "
            "place unannotated."
        ),
        ("dynamic", "structure stack", "reference stack", "skip"),
        assume_yes=assume_yes,
    )
    return {
        "dynamic": TYPE_DYNAMIC,
        "structure stack": TYPE_STRUCTURE,
        "reference stack": TYPE_REFSTACK,
        "skip": "skip",
    }[selected]


def _review_classifications(
    classifications: Dict[Path, str],
    session_dir: Path,
) -> Dict[Path, str]:
    """Show the automatic classification and let the operator confirm or redo.

    Displays every .meta file with its automatically determined type and
    destination, then offers: (1) confirm and proceed, or (2) reclassify each
    file manually (1/2/3/4 prompts, current classification as the default).
    Loops until the operator confirms.
    """
    digit_by_type = {
        TYPE_DYNAMIC: "1",
        TYPE_STRUCTURE: "2",
        TYPE_REFSTACK: "3",
        "skip": "4",
    }
    type_by_digit = {
        "1": TYPE_DYNAMIC,
        "2": TYPE_STRUCTURE,
        "3": TYPE_REFSTACK,
        "4": "skip",
    }

    while True:
        print("\nAutomatic classification of .meta files:")
        for meta_path in sorted(classifications):
            rel = meta_path.relative_to(session_dir)
            print(f"  {classifications[meta_path]:<10} {rel}")
        print(
            "(dynamic -> dynamic_data/, structure -> static_data/, "
            "ref_stack -> dynamic_data/reference_stack/, skip -> left in place)"
        )

        selected = _prompt_choice(
            "Review the classification above; files are moved and annotated accordingly",
            (
                "confirm: the classification looks good",
                "reclassify: choose each file's type manually",
            ),
        )
        if selected.startswith("confirm"):
            return classifications

        for meta_path in sorted(classifications):
            rel = meta_path.relative_to(session_dir)
            current = classifications[meta_path]
            default_digit = digit_by_type.get(current, "4")
            while True:
                raw = _prompt(
                    f"Classify '{rel}' (1=dynamic, 2=structure, 3=ref_stack, 4=skip)",
                    default_digit,
                ).strip()
                if raw in type_by_digit:
                    classifications[meta_path] = type_by_digit[raw]
                    break
                print("Invalid selection. Enter 1, 2, 3, or 4.")


def _collect_siblings(meta_path: Path) -> List[Path]:
    stem = meta_path.stem
    return list(meta_path.parent.glob(f"{stem}*"))


def _build_normalized_stem(file_type: str, original_stem: str) -> str:
    """Normalize a stem to its canonical SLAP2 prefix.

    dynamic -> acquisition_..., structure -> structure_..., ref_stack -> refStack_...

    The leading token of a stem is a free string typed by the operator in the
    SLAP2 software; it is replaced by the canonical prefix. A stem that
    already starts with the canonical prefix is left unchanged — stripping
    further tokens would collapse distinct acquisitions onto the same stem.
    """
    base = original_stem.replace(" ", "_")
    prefix_map = {
        TYPE_DYNAMIC: "acquisition",
        TYPE_STRUCTURE: "structure",
        TYPE_REFSTACK: "refStack",
    }
    prefix = prefix_map.get(file_type, file_type)
    if base.lower().startswith(f"{prefix.lower()}_"):
        return base
    base_tail = base.split("_", 1)[1] if "_" in base else base
    return f"{prefix}_{base_tail}"


def _normalize_channel_targets(value) -> List[str]:
    """Normalize an intended-channel-target value to a list of strings.

    Matches the metadata editor's convention: [] = not yet filled,
    ["None"] = explicit "deliberately no indicator". Accepts the legacy
    single-string form, a list, or None.
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    s = str(value).strip()
    return [s] if s else []


def _build_annotation_payload(
    file_type: str,
    *,
    original_stem: str,
    normalized_stem: str,
    moved_files: List[str],
    source_rel: str,
    dest_rel_dir: str,
    pia_depth_on_remote_focus_um: float | None,
    target_name_value: str | None,
    targeted_structure_value: str,
    intended_green_target,
    intended_red_target,
    slap2_mode_value: str,
    operator: str | None,
    stage_offset: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """Build an annotation payload in the unified GUI/ETL schema.

    The field sets mirror the metadata editor's _apply_dynamic_defaults /
    _apply_static_defaults (which in turn mirror what
    generate_acquisition_json consumes), plus this module's structural
    bookkeeping keys. target_name is not stored: the FOV/Neuron answer is
    parsed into the neuron_id / fov_index fields the ETL actually reads.
    Human-required fields with no known value are left at detectable
    defaults (fov_index -1, targeted_structure "", indicators []) for the
    metadata editor's save-time validation to enforce.
    """
    bookkeeping = {
        "original_stem": original_stem,
        "normalized_stem": normalized_stem,
        "type": file_type,
        "moved_files": moved_files,
        "source_rel": source_rel,
        "dest_dir": dest_rel_dir,
    }

    if file_type == TYPE_REFSTACK:
        # Ref-stack annotations keep the legacy structural payload: the
        # metadata editor never loads them and the ETL does not read
        # per-file ref-stack metadata.
        return {
            **bookkeeping,
            "pia_depth_on_remote_focus_um": pia_depth_on_remote_focus_um,
            "target_name": target_name_value,
            "targeted_structure": targeted_structure_value,
            "intended_green_channel_target": intended_green_target,
            "intended_red_channel_target": intended_red_target,
            "slap2_mode": slap2_mode_value,
            "operator": operator,
        }

    kind, number = _parse_target_name(target_name_value)
    neuron_id = number if kind == "NEURON" else None
    fov_index = number if kind == "FOV" else -1

    payload: Dict[str, Any] = {
        "stage_offset": stage_offset,
        "pia_depth_on_remote_focus_um": pia_depth_on_remote_focus_um,
        "intended_red_channel_target": _normalize_channel_targets(intended_red_target),
        "intended_green_channel_target": _normalize_channel_targets(intended_green_target),
        "neuron_id": neuron_id,
        "targeted_structure": targeted_structure_value or "",
        "operator": operator or "",
        **bookkeeping,
    }

    if file_type == TYPE_DYNAMIC:
        payload["fov_index"] = fov_index
        payload["hwp_laser_power"] = -1.0
        payload["slap2_mode"] = slap2_mode_value or ""
        payload["acquisition_type"] = ""
        for structure in ("dendrite", "axon", "soma"):
            payload[f"{structure}_planes_raster"] = []
            payload[f"{structure}_planes_integration"] = []
    else:  # TYPE_STRUCTURE -> static annotation schema
        payload["hwp_laser_power"] = None

    return payload


def _write_annotation(annotation_path: Path, payload: Dict[str, Any]) -> None:
    annotation_path.parent.mkdir(parents=True, exist_ok=True)
    annotation_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _collect_launcher_metadata(session_dir: Path) -> List[str]:
    metadata_dir = session_dir / "launcher_metadata"
    if not metadata_dir.exists():
        return []
    return [p.relative_to(session_dir).as_posix() for p in metadata_dir.rglob("*") if p.is_file()]


def _warn_metadata_incomplete(reason: str) -> None:
    """Loud, non-fatal operator warning used by the GUI pass (Phase B)."""
    message = (
        f"{reason}\n"
        "Session metadata is still incomplete: run the SLAP2 metadata editor "
        "on this session folder later. Upload validation will refuse this "
        "session until the required metadata has been filled in and saved."
    )
    LOG.warning(message)
    print("\nWARNING: " + message)


def _gui_pass(
    session_dir: Path,
    params: Dict[str, Any],
    *,
    assume_yes: bool,
    has_annotatable_data: bool,
) -> None:
    """Phase B: open the SLAP2 metadata editor GUI on the organized session.

    Never raises and never fails the launcher: every problem degrades to a
    warning telling the operator to run the editor later (upload validation
    is the backstop that refuses incomplete metadata).
    """
    if not bool(params.get("open_gui", True)):
        LOG.info("Metadata editor disabled by param (open_gui=false); skipping GUI pass.")
        return
    if assume_yes:
        _warn_metadata_incomplete(
            "assume_yes is set (headless run): NOT opening the metadata editor."
        )
        return
    if not has_annotatable_data and not bool(params.get("open_gui_when_empty", False)):
        LOG.info(
            "No organized acquisition folders to annotate; skipping metadata "
            "editor (set open_gui_when_empty=true to open it anyway)."
        )
        return

    try:
        from slap2_onprem_handling.metadata_editor import run_editor
    except ImportError as exc:
        _warn_metadata_incomplete(
            f"The SLAP2 metadata editor is not installed ({exc}). "
            "Install the launcher with the [slap2] extra to enable it."
        )
        return

    LOG.info("Opening SLAP2 metadata editor for %s", session_dir)
    try:
        saved = run_editor(session_dir, folder_layout="rig")
    except Exception as exc:  # noqa: BLE001
        LOG.warning("Metadata editor raised an error", exc_info=True)
        _warn_metadata_incomplete(f"The SLAP2 metadata editor could not run ({exc}).")
        return

    if saved:
        LOG.info("Metadata editor closed; metadata was saved.")
    else:
        _warn_metadata_incomplete("The metadata editor was closed WITHOUT saving.")


_RECONCILED_ENTRY_TYPE = "reconciled_files"


def _reconcile_manifest(
    session_dir: Path,
    routing_manifest_path: Path,
    *,
    scan_rel_dirs: Tuple[str, ...],
    extra_root_files: Tuple[str, ...] = ("postacq_annotations.h5",),
) -> None:
    """Register files in the convention dirs (plus named session-root files)
    that are not yet listed in the routing manifest.

    The routing manifest gates what the archiver copies to the network share;
    files created after the mechanical pass (editor-written annotations,
    GIAnT's postacq_annotations.h5, rig-side extras like rigDescription.json)
    must be added or they would silently be left behind.

    Safety: if no manifest exists, do NOT create one — without a manifest the
    archiver copies the whole session, and creating one here that lists only
    stragglers would exclude the actual data.
    """
    if not routing_manifest_path.exists():
        LOG.info(
            "No routing manifest at %s; skipping reconciliation (the archiver "
            "copies the whole session when no manifest exists).",
            routing_manifest_path,
        )
        return
    entries = manifest_utils.read_manifest_entries(routing_manifest_path)
    if not entries:
        return

    known: set = set()
    for entry in entries:
        known.update(entry.get("files") or [])

    extras: List[str] = []
    scanned: List[Path] = []
    for rel_dir in scan_rel_dirs:
        base = session_dir / rel_dir
        if not base.is_dir():
            continue
        # Skip dirs nested inside an already-scanned dir (e.g. the default
        # ref-stack dir lives under the dynamic dir); rglob covered them.
        if any(prev == base or prev in base.parents for prev in scanned):
            continue
        scanned.append(base)
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(session_dir).as_posix()
            if rel not in known:
                extras.append(rel)
                known.add(rel)

    for name in extra_root_files:
        if (session_dir / name).is_file() and name not in known:
            extras.append(name)
            known.add(name)

    if not extras:
        return

    existing = next((e for e in entries if e.get("type") == _RECONCILED_ENTRY_TYPE), None)
    if existing:
        files = set(existing.get("files") or [])
        files.update(extras)
        existing["files"] = sorted(files)
    else:
        entries.append({"type": _RECONCILED_ENTRY_TYPE, "files": sorted(extras)})
    manifest_utils.write_manifest(routing_manifest_path, entries)
    LOG.info(
        "Routing manifest reconciled: registered %d additional file(s): %s",
        len(extras),
        ", ".join(sorted(extras)),
    )


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
    # No hardcoded fallback: a plausible-looking default (e.g. "VISp") stamped
    # into every annotation can ship wrong metadata unnoticed; blank values
    # are enforced later by the metadata editor's save-time validation.
    default_targeted_structure = params.get("default_targeted_structure")
    if default_targeted_structure is None:
        default_targeted_structure = params.get("default_brain_area")

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

    # Item 15: close the on-rig notes editor (if the notes step left one
    # open) before any interactive work. Best-effort, never fatal; only a
    # process still running the expected editor image is ever terminated.
    if bool(params.get("close_notes_editor", True)):
        notes_filename = params.get("experiment_notes_filename", "experiment_notes.txt")
        notes_path = Path(str(notes_filename)).expanduser()
        if not notes_path.is_absolute():
            notes_path = session_dir / notes_path
        expected_image = notes_editor.expected_image_from_command(
            params.get("experiment_notes_editor_command", notes_editor.DEFAULT_EDITOR_IMAGE)
        )
        if notes_editor.close_notes_editor(notes_path, expected_image=expected_image):
            LOG.info("Closed experiment notes editor before annotation.")

    # ---- Prefill values from pack parameters (no metadata prompts) --------
    # Metadata entry is the metadata editor GUI's job (Phase B); the pack may
    # supply session-level defaults that are stamped into the scaffold
    # annotations as PREFILL for the operator to confirm or override there.
    # Anything not supplied stays blank — the editor's save-time validation
    # enforces the required fields.
    targeted_structure_value = str(default_targeted_structure or "")
    intended_green_target = params.get("default_green_channel_target")
    intended_red_target = params.get("default_red_channel_target")
    slap2_mode_value = str(params.get("default_slap2_mode") or "")
    target_name_value = (
        str(params.get("default_target_name"))
        if params.get("default_target_name")
        else None
    )

    def _pia_default(device: Optional[str]) -> Optional[float]:
        if device not in ("dmd1", "dmd2"):
            return None
        raw = params.get(f"default_pia_depth_on_remote_focus_{device}_um")
        if raw is None:
            raw = params.get(f"default_{device}_depth")  # legacy key
        if raw in (None, ""):
            return None
        try:
            return float(raw)
        except Exception:  # noqa: BLE001
            return None

    def _stage_offset_default(key: str) -> Optional[List[float]]:
        """Parse a pack-supplied per-type stage offset ([x, y] list)."""
        raw = params.get(key)
        if raw in (None, ""):
            return None
        try:
            offset = [float(v) for v in raw]
        except Exception:  # noqa: BLE001
            LOG.warning("Ignoring malformed %s (expected [x, y] list): %r", key, raw)
            return None
        if len(offset) != 2:
            LOG.warning("Ignoring malformed %s (expected 2 values): %r", key, raw)
            return None
        return offset

    stage_offset_by_type = {
        TYPE_DYNAMIC: _stage_offset_default("default_dynamic_stage_offset"),
        TYPE_STRUCTURE: _stage_offset_default("default_static_stage_offset"),
        TYPE_REFSTACK: None,
    }

    dynamic_prefixes = _normalize_prefixes(
        params.get("dynamic_stem_prefixes"), _BUILTIN_DYNAMIC_PREFIXES
    )
    structure_prefixes = _normalize_prefixes(
        params.get("structure_stem_prefixes"), _BUILTIN_STRUCTURE_PREFIXES
    )
    ref_stack_prefixes = _normalize_prefixes(
        params.get("ref_stack_stem_prefixes"), _BUILTIN_REF_STACK_PREFIXES
    )

    entries: List[Dict[str, Any]] = manifest_utils.read_manifest_entries(routing_manifest_path)
    used_stems: Dict[str, set] = {}

    meta_files = sorted(session_dir.rglob("*.meta"))
    if not meta_files:
        LOG.warning("No .meta files found under %s", session_dir)
        has_annotatable_data = (
            (session_dir / dynamic_dir).is_dir() or (session_dir / structure_dir).is_dir()
        )
        _gui_pass(
            session_dir,
            params,
            assume_yes=assume_yes,
            has_annotatable_data=has_annotatable_data,
        )
        _reconcile_manifest(
            session_dir,
            routing_manifest_path,
            scan_rel_dirs=(dynamic_dir, structure_dir, ref_stack_dir),
        )
        return 0

    # ---- Classification pass: classify every file automatically first ----
    # Files are grouped per acquisition (DMD1/DMD2 pair); a group is
    # classified by its first member that resolves silently (contents or
    # recognized prefix), so one unreadable/oddly-named partner never forces
    # a prompt when the other can answer. Only unresolved groups prompt.
    groups: Dict[str, List[Path]] = {}
    for meta_path in meta_files:
        groups.setdefault(_meta_group_key(meta_path), []).append(meta_path)

    classify_kwargs = dict(
        dynamic_prefixes=dynamic_prefixes,
        structure_prefixes=structure_prefixes,
        ref_stack_prefixes=ref_stack_prefixes,
        assume_yes=assume_yes,
    )

    classifications: Dict[Path, str] = {}
    for group_key, members in groups.items():
        type_choice: Optional[str] = None
        for member in members:
            type_choice = _classify_meta(
                member, session_dir, silent_only=True, **classify_kwargs
            )
            if type_choice is not None:
                break
        if type_choice is None:
            type_choice = _classify_meta(members[0], session_dir, **classify_kwargs)
        for member in members:
            if member not in classifications:
                classifications[member] = type_choice
                LOG.info(
                    "Classification for %s: %s",
                    member.relative_to(session_dir),
                    type_choice,
                )

    # ---- Review: show the result, let the operator confirm or reclassify ----
    if not assume_yes:
        classifications = _review_classifications(classifications, session_dir)

    # ---- Processing pass: move files and write annotations ----
    skipped_meta_files: List[Path] = []
    for meta_path in meta_files:
        stem_lower = meta_path.stem.lower()
        type_choice = classifications[meta_path]

        if type_choice == "skip":
            LOG.info("Skipping meta file: %s", meta_path)
            skipped_meta_files.append(meta_path)
            continue

        device = None
        if "dmd1" in stem_lower:
            device = "dmd1"
        elif "dmd2" in stem_lower:
            device = "dmd2"

        pia_depth_on_remote_focus_um = _pia_default(device)

        if type_choice == TYPE_DYNAMIC:
            dest_rel_dir = dynamic_dir
        elif type_choice == TYPE_STRUCTURE:
            dest_rel_dir = structure_dir
        else:
            dest_rel_dir = ref_stack_dir

        dest_dir = session_dir / dest_rel_dir

        # Re-run safety: .meta discovery is recursive, so a second annotator
        # run finds files it already organized. Leave them exactly as they
        # are — re-moving would mangle names (_dup suffixes) and re-writing
        # the annotation would destroy operator-entered metadata. The
        # manifest reconciliation pass re-registers them if needed.
        if meta_path.parent == dest_dir:
            LOG.info(
                "Already organized under %s; leaving files and any existing "
                "annotation untouched: %s",
                dest_rel_dir,
                meta_path.relative_to(session_dir),
            )
            continue

        dest_dir.mkdir(parents=True, exist_ok=True)

        # Disambiguate colliding normalized stems (two differently-named
        # acquisitions can normalize to the same stem): a collision would
        # silently overwrite the first acquisition's annotation.
        normalized_stem = _build_normalized_stem(type_choice, meta_path.stem)
        candidate = normalized_stem
        occurrence = 1
        while (
            candidate in used_stems.setdefault(dest_rel_dir, set())
            or (dest_dir / f"{candidate}.annotation.json").exists()
        ):
            occurrence += 1
            candidate = f"{normalized_stem}_{occurrence}"
        if candidate != normalized_stem:
            LOG.warning(
                "Normalized stem collision for %s: using %s",
                meta_path.relative_to(session_dir),
                candidate,
            )
        normalized_stem = candidate
        used_stems[dest_rel_dir].add(normalized_stem)

        siblings = _collect_siblings(meta_path)
        planned: List[Tuple[Path, Path]] = []
        for src in siblings:
            rel_name = src.name.replace(meta_path.stem, normalized_stem, 1)
            planned.append((src, dest_dir / rel_name))

        LOG.info("Planned moves for %s -> %s", meta_path.stem, dest_rel_dir)
        for src, dst in planned:
            LOG.info("  %s -> %s", src.relative_to(session_dir), dst.relative_to(session_dir))

        moved_files: List[str] = []
        for src, dst in planned:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                dst = dst.with_name(dst.stem + "_dup" + dst.suffix)
            shutil.move(str(src), dst)
            moved_files.append(dst.relative_to(session_dir).as_posix())

        annotation_path = dest_dir / f"{normalized_stem}.annotation.json"
        annotation_payload = _build_annotation_payload(
            type_choice,
            original_stem=meta_path.stem,
            normalized_stem=normalized_stem,
            moved_files=moved_files,
            source_rel=meta_path.relative_to(session_dir).as_posix(),
            dest_rel_dir=dest_rel_dir,
            pia_depth_on_remote_focus_um=pia_depth_on_remote_focus_um,
            target_name_value=target_name_value,
            targeted_structure_value=targeted_structure_value,
            intended_green_target=intended_green_target,
            intended_red_target=intended_red_target,
            slap2_mode_value=slap2_mode_value,
            operator=params.get("user_id") or params.get("operator"),
            stage_offset=stage_offset_by_type.get(type_choice),
        )
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

    if skipped_meta_files:
        skipped_list = "\n".join(
            f"  {p.relative_to(session_dir)}" for p in skipped_meta_files
        )
        message = (
            "UNCLASSIFIED LEFTOVERS: %d .meta file(s) were skipped and remain "
            "in place, unannotated, and NOT listed in the routing manifest — "
            "they will not be copied to the network archive:\n%s\n"
            "Re-run the annotator interactively (or fix the file names / "
            "declare stem prefixes in the param pack) to classify them."
        )
        LOG.warning(message, len(skipped_meta_files), skipped_list)
        print("\n" + message % (len(skipped_meta_files), skipped_list))

    # ---- Phase B: metadata editor GUI on the organized session ----
    has_annotatable_data = (
        (session_dir / dynamic_dir).is_dir() or (session_dir / structure_dir).is_dir()
    )
    _gui_pass(
        session_dir,
        params,
        assume_yes=assume_yes,
        has_annotatable_data=has_annotatable_data,
    )

    # ---- Reconcile: register files created after the mechanical pass ----
    _reconcile_manifest(
        session_dir,
        routing_manifest_path,
        scan_rel_dirs=(dynamic_dir, structure_dir, ref_stack_dir),
    )

    return 0


def run_post_acquisition(param_file: Union[str, Dict[str, Any]], overrides: Optional[Dict[str, Any]] = None) -> int:
    try:
        params = param_utils.load_parameters(param_file=param_file, overrides=overrides)
        return run(params)
    except Exception as exc:  # noqa: BLE001
        LOG.error("SLAP2 meta annotation failed: %s", exc, exc_info=True)
        return 1
