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

NONE_CHOICE = "None"
INDICATOR_TARGETS_PATH = Path(__file__).with_name("indicator_targets.json")

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


def _load_indicator_targets(path: Path) -> Dict[str, List[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    targets: Dict[str, List[str]] = {}
    for key in ("green_channel_targets", "red_channel_targets"):
        values = payload.get(key)
        if not isinstance(values, list) or not values or not all(
            isinstance(value, str) and value.strip() for value in values
        ):
            raise ValueError(f"{path} must contain a non-empty string list named '{key}'")
        targets[key] = values
    return targets


def _write_indicator_targets(path: Path, targets: Dict[str, List[str]]) -> None:
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(json.dumps(targets, indent=2) + "\n", encoding="utf-8")
    temporary_path.replace(path)


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


def _prompt_indicator_choice(
    message: str,
    channel_key: str,
    indicator_targets: Dict[str, List[str]],
    indicator_targets_path: Path,
    *,
    default: Union[str, List[str], None] = None,
    assume_yes: bool = False,
) -> Union[str, List[str], None]:
    if isinstance(default, list):
        selected = [str(value) for value in default if str(value).strip()]
    elif default and default != NONE_CHOICE:
        selected = [str(default)]
    else:
        selected = []

    def _result() -> Union[str, List[str], None]:
        if not selected:
            return None
        if len(selected) == 1:
            return selected[0]
        return selected

    if assume_yes:
        return _result()

    while True:
        choices = indicator_targets[channel_key] + [NONE_CHOICE, "Done"]
        choice_lines = [f"{idx + 1}) {value}" for idx, value in enumerate(choices)]
        selected_display = ", ".join(selected) if selected else "None"
        prompt_message = (
            f"\n=== {message} ===\n"
            + f"Currently selected: {selected_display}\n"
            + "\n".join(choice_lines)
            + '\nType "new" to add a new indicator to the list.'
        )
        done_index = str(len(choices))
        raw = _prompt(f"{prompt_message}\nSelect an indicator or Done", done_index).strip()

        if raw.isdigit():
            index = int(raw) - 1
            if 0 <= index < len(choices):
                raw = choices[index]
        for value in choices:
            if raw.lower() == value.lower():
                raw = value
                break

        if raw == "Done":
            return _result()
        if raw == NONE_CHOICE:
            selected.clear()
            print("Cleared indicators for this channel. Select Done to continue.")
            continue
        matching_target = next(
            (value for value in indicator_targets[channel_key] if raw.lower() == value.lower()),
            None,
        )
        if matching_target is not None:
            if matching_target not in selected:
                selected.append(matching_target)
                print(f'Selected indicator "{matching_target}".')
            else:
                print(f'Indicator "{matching_target}" is already selected.')
            continue

        if raw.lower() != "new":
            print('Invalid selection. Choose a number, type "new", or select Done.')
            continue

        while True:
            indicator = _prompt("Indicator string").strip()
            confirmation = _prompt("Confirm indicator string").strip()
            if not indicator:
                print("Indicator cannot be empty. Please enter it again.")
                continue
            if indicator != confirmation:
                print("Indicator strings do not match. Please enter them again.")
                continue

            while True:
                confirmed = _prompt(
                    f'Add indicator "{indicator}" to this channel list? (yes/no)'
                ).strip().lower()
                if confirmed in {"yes", "y"}:
                    existing = next(
                        (
                            value
                            for value in indicator_targets[channel_key]
                            if value.lower() == indicator.lower()
                        ),
                        None,
                    )
                    if existing is not None:
                        print(f'Indicator "{existing}" is already in the list.')
                        print("Select an indicator from the updated list.")
                        break
                    indicator_targets[channel_key].append(indicator)
                    _write_indicator_targets(indicator_targets_path, indicator_targets)
                    print(f'Added indicator "{indicator}" to the list.')
                    print("Select an indicator from the updated list.")
                    break
                if confirmed in {"no", "n"}:
                    print("Indicator was not added.")
                    break
                print("Please answer yes or no.")
            break


_DMD_SUFFIX_RE = re.compile(r"([_\- ]dmd[12])$", re.IGNORECASE)


def _meta_group_key(meta_path: Path) -> str:
    """Group meta files so DMD1/DMD2 variants share prompts.

    Many acquisitions generate two files (DMD1/DMD2). We want to prompt once per
    acquisition (per stem without the DMD suffix) and apply to both.
    """

    stem = meta_path.stem
    return _DMD_SUFFIX_RE.sub("", stem)


def _infer_type(stem_lower: str) -> str:
    if stem_lower.startswith(_BUILTIN_DYNAMIC_PREFIXES):
        return TYPE_DYNAMIC
    if stem_lower.startswith(_BUILTIN_STRUCTURE_PREFIXES):
        return TYPE_STRUCTURE
    if stem_lower.startswith(_BUILTIN_REF_STACK_PREFIXES):
        return TYPE_REFSTACK
    return TYPE_UNKNOWN


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
    stack_split_memory: Dict[str, str],
    fallback_memory: Dict[str, str],
    assume_yes: bool,
) -> str:
    """Classify a .meta file as TYPE_DYNAMIC/TYPE_STRUCTURE/TYPE_REFSTACK or "skip".

    Decision ladder:
      1. .meta contents (enableStack): 0 -> dynamic, machine truth, silent.
      2. enableStack == 1 -> a z-stack; the filename prefix (or a remembered
         operator answer) picks structure vs. reference stack; else ONE
         contextual two-choice prompt.
      3. Contents unreadable -> filename prefix; unknown prefixes use a
         remembered answer or ONE contextual prompt (no default — invalid
         input re-prompts rather than silently classifying as dynamic).
    Under assume_yes, files that would need a prompt are skipped loudly:
    guessing a classification can misfile data.
    """
    rel = meta_path.relative_to(session_dir)
    stem_lower = meta_path.stem.lower()
    prefix_key = stem_lower.split("_", 1)[0]

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
        if inferred == TYPE_DYNAMIC:
            LOG.warning(
                "Filename of %s looks dynamic but .meta contents say z-stack; "
                "trusting the contents and asking the operator",
                rel,
            )
        if prefix_key in stack_split_memory:
            choice = stack_split_memory[prefix_key]
            LOG.info(
                "Classified %s as %s (reusing earlier answer for '%s*' files)",
                rel,
                choice,
                prefix_key,
            )
            return choice
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
        choice = TYPE_STRUCTURE if selected == "structure stack" else TYPE_REFSTACK
        stack_split_memory[prefix_key] = choice
        return choice

    # Contents unreadable -> filename prefix fallback.
    inferred = _prefix_type()
    if inferred != TYPE_UNKNOWN:
        LOG.info("Classified %s as %s (filename prefix)", rel, inferred)
        return inferred
    if prefix_key in fallback_memory:
        choice = fallback_memory[prefix_key]
        LOG.info(
            "Classified %s as %s (reusing earlier answer for '%s*' files)",
            rel,
            choice,
            prefix_key,
        )
        return choice
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
    choice = {
        "dynamic": TYPE_DYNAMIC,
        "structure stack": TYPE_STRUCTURE,
        "reference stack": TYPE_REFSTACK,
        "skip": "skip",
    }[selected]
    if choice != "skip":
        fallback_memory[prefix_key] = choice
    return choice


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
        "stage_offset": None,
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
    indicator_targets_path = Path(
        str(params.get("indicator_targets_path", INDICATOR_TARGETS_PATH))
    ).expanduser().resolve()
    indicator_targets = _load_indicator_targets(indicator_targets_path)

    intended_green_target = _prompt_indicator_choice(
        "GREEN CHANNEL: Intended Target(s)",
        "green_channel_targets",
        indicator_targets,
        indicator_targets_path,
        default=green_target_default,
        assume_yes=assume_yes,
    )
    intended_red_target = _prompt_indicator_choice(
        "RED CHANNEL: Intended Target(s)",
        "red_channel_targets",
        indicator_targets,
        indicator_targets_path,
        default=red_target_default,
        assume_yes=assume_yes,
    )

    # Per-acquisition (DMD1/DMD2 pair) prompts.
    modes_by_group: Dict[str, str] = {}

    # Classification caches: DMD pairs share one classification; operator
    # answers for unknown stem prefixes are remembered within the session.
    type_by_group: Dict[str, str] = {}
    stack_split_memory: Dict[str, str] = {}
    fallback_memory: Dict[str, str] = {}
    dynamic_prefixes = _normalize_prefixes(
        params.get("dynamic_stem_prefixes"), _BUILTIN_DYNAMIC_PREFIXES
    )
    structure_prefixes = _normalize_prefixes(
        params.get("structure_stem_prefixes"), _BUILTIN_STRUCTURE_PREFIXES
    )
    ref_stack_prefixes = _normalize_prefixes(
        params.get("ref_stack_stem_prefixes"), _BUILTIN_REF_STACK_PREFIXES
    )

    # Per-DMD defaults (prompted once per DMD) used for per-file pia depth prompt.
    pia_depth_default_by_device: Dict[str, float | None] = {}

    entries: List[Dict[str, Any]] = manifest_utils.read_manifest_entries(routing_manifest_path)
    counter = 1

    meta_files = sorted(session_dir.rglob("*.meta"))
    if not meta_files:
        LOG.warning("No .meta files found under %s", session_dir)
        return 0

    # ---- Classification pass: classify every file automatically first ----
    classifications: Dict[Path, str] = {}
    for meta_path in meta_files:
        group_key = _meta_group_key(meta_path)
        if group_key in type_by_group:
            type_choice = type_by_group[group_key]
            LOG.info(
                "Classified %s as %s (same acquisition group as its DMD partner)",
                meta_path.relative_to(session_dir),
                type_choice,
            )
        else:
            type_choice = _classify_meta(
                meta_path,
                session_dir,
                dynamic_prefixes=dynamic_prefixes,
                structure_prefixes=structure_prefixes,
                ref_stack_prefixes=ref_stack_prefixes,
                stack_split_memory=stack_split_memory,
                fallback_memory=fallback_memory,
                assume_yes=assume_yes,
            )
            type_by_group[group_key] = type_choice
        classifications[meta_path] = type_choice

    # ---- Review: show the result, let the operator confirm or reclassify ----
    if not assume_yes:
        classifications = _review_classifications(classifications, session_dir)

    # ---- Processing pass: move files and write annotations ----
    for meta_path in meta_files:
        stem_lower = meta_path.stem.lower()
        group_key = _meta_group_key(meta_path)
        type_choice = classifications[meta_path]

        if type_choice == "skip":
            LOG.info("Skipping meta file: %s", meta_path)
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

    return 0
def run_post_acquisition(param_file: Union[str, Dict[str, Any]], overrides: Optional[Dict[str, Any]] = None) -> int:
    try:
        params = param_utils.load_parameters(param_file=param_file, overrides=overrides)
        return run(params)
    except Exception as exc:  # noqa: BLE001
        LOG.error("SLAP2 meta annotation failed: %s", exc, exc_info=True)
        return 1
