from __future__ import annotations

import json
from pathlib import Path

import pytest

from openscope_experimental_launcher.post_acquisition import slap2_meta_annotator


class InputFeeder:
    def __init__(self, replies):
        self._replies = list(replies)
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self._replies:
            raise AssertionError(f"No more replies left for prompt: {prompt}")
        return self._replies.pop(0)


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"test")


def test_default_indicator_targets_are_colocated_with_plugin():
    module_path = Path(slap2_meta_annotator.__file__)

    assert slap2_meta_annotator.INDICATOR_TARGETS_PATH.parent == module_path.parent
    targets = slap2_meta_annotator._load_indicator_targets(
        slap2_meta_annotator.INDICATOR_TARGETS_PATH
    )
    assert targets["green_channel_targets"]
    assert targets["red_channel_targets"]


def test_new_indicator_requires_matching_confirmation_and_updates_channel(tmp_path, monkeypatch, capsys):
    targets_path = tmp_path / "indicator_targets.json"
    targets_path.write_text(
        json.dumps(
            {
                "green_channel_targets": ["GFP"],
                "red_channel_targets": ["jRGECO1a"],
            }
        ),
        encoding="utf-8",
    )
    targets = slap2_meta_annotator._load_indicator_targets(targets_path)
    feeder = InputFeeder(
        [
            "new",
            "GCaMP8f",
            "GCaMP8s",
            "GCaMP8f",
            "GCaMP8f",
            "maybe",
            "yes",
            "2",
            "done",
        ]
    )
    monkeypatch.setattr("builtins.input", feeder)

    selected = slap2_meta_annotator._prompt_indicator_choice(
        "GREEN CHANNEL: Intended Target(s)",
        "green_channel_targets",
        targets,
        targets_path,
    )

    assert selected == "GCaMP8f"
    saved = json.loads(targets_path.read_text(encoding="utf-8"))
    assert saved["green_channel_targets"] == ["GFP", "GCaMP8f"]
    assert saved["red_channel_targets"] == ["jRGECO1a"]
    combined_prompts = "\n".join(feeder.prompts)
    assert 'Type "new" to add a new indicator to the list.' in combined_prompts
    assert combined_prompts.count("GREEN CHANNEL: Intended Target(s)") == 3
    assert 'Add indicator "GCaMP8f" to this channel list? (yes/no)' in combined_prompts
    output = capsys.readouterr().out
    assert "Indicator strings do not match" in output
    assert "Please answer yes or no" in output


def test_indicator_choice_returns_list_for_multiple_selections(tmp_path, monkeypatch):
    targets_path = tmp_path / "indicator_targets.json"
    targets_path.write_text(
        json.dumps(
            {
                "green_channel_targets": ["GFP", "GCaMP8f"],
                "red_channel_targets": ["jRGECO1a"],
            }
        ),
        encoding="utf-8",
    )
    targets = slap2_meta_annotator._load_indicator_targets(targets_path)
    monkeypatch.setattr("builtins.input", InputFeeder(["1", "2", "done"]))

    selected = slap2_meta_annotator._prompt_indicator_choice(
        "GREEN CHANNEL: Intended Target(s)",
        "green_channel_targets",
        targets,
        targets_path,
    )

    assert selected == ["GFP", "GCaMP8f"]


def test_prompts_experiment_once_and_mode_once_per_dmd_pair(tmp_path, monkeypatch):
    session_dir = tmp_path / "session"
    session_dir.mkdir()

    # Two meta files that represent the same acquisition but different DMDs.
    dmd1 = session_dir / "acquisition_foo_DMD1.meta"
    dmd2 = session_dir / "acquisition_foo_DMD2.meta"
    _touch(dmd1)
    _touch(dmd2)

    # Sibling files for the same stems should move together.
    _touch(session_dir / "acquisition_foo_DMD1.h5")
    _touch(session_dir / "acquisition_foo_DMD2.h5")

    feeder = InputFeeder(
        [
            # Default targeted structure
            "VISp",
            # Green target: select 1
            "1",
            # Finish green target selection
            "done",
            # Red target: select 1
            "1",
            # Finish red target selection
            "done",
            # First meta: classify (dynamic)
            "1",
            # Mode for acquisition_foo (shared)
            "1",
            # Default pia depth for DMD1
            "120",
            # Pia depth override for DMD1 meta (accept default)
            "",
            # Target name for first meta: type (default FOV)
            "",
            # Target name for first meta: number
            "1",
            # Targeted structure for first meta
            "VISp",
            # Confirm moves
            "y",
            # Second meta: classify (dynamic)
            "1",
            # Default pia depth for DMD2
            "220",
            # Pia depth override for DMD2 meta
            "240",
            # Target name for second meta: type
            "Neuron",
            # Target name for second meta: number
            "2",
            # Targeted structure for second meta
            "VISp",
            # Confirm moves
            "y",
        ]
    )

    monkeypatch.setattr("builtins.input", feeder)

    params = {
        "output_session_folder": str(session_dir),
        "assume_yes": False,
        "validate_targeted_structure_ccf": False,
        "dynamic_dir": "dynamic_data",
        "structure_dir": "static_data",
        "ref_stack_dir": "dynamic_data/reference_stack",
        "manifest_name": "routing_manifest.json",
        "user_id": "operator1",
    }

    result = slap2_meta_annotator.run(params)
    assert result == 0

    # Ensure experiment-level prompts occurred once.
    combined_prompts = "\n".join(feeder.prompts)
    assert combined_prompts.count("GREEN CHANNEL: Intended Target(s)") == 2
    assert combined_prompts.count("RED CHANNEL: Intended Target(s)") == 2

    # Ensure mode prompt occurred once for the DMD pair.
    assert combined_prompts.count("SLAP2 Modes") == 1

    # Verify annotations exist and are in the unified GUI/ETL schema.
    annotations = list(session_dir.rglob("*.annotation.json"))
    assert len(annotations) == 2

    for annotation_path in annotations:
        payload = json.loads(annotation_path.read_text(encoding="utf-8"))
        assert payload["intended_green_channel_target"]
        assert payload["intended_red_channel_target"]
        assert payload["slap2_mode"]
        assert payload["pia_depth_on_remote_focus_um"] is not None
        assert "target_name" not in payload
        assert payload["targeted_structure"]

    # target_name answers are parsed into neuron_id / fov_index.
    by_stem = {}
    for p in annotations:
        payload = json.loads(p.read_text(encoding="utf-8"))
        by_stem[payload["original_stem"]] = payload
    dmd1_payload = by_stem["acquisition_foo_DMD1"]
    dmd2_payload = by_stem["acquisition_foo_DMD2"]
    assert dmd1_payload["fov_index"] == 1  # answered FOV 1
    assert dmd1_payload["neuron_id"] is None
    assert dmd2_payload["neuron_id"] == 2  # answered Neuron 2
    assert dmd2_payload["fov_index"] == -1  # unfilled sentinel


def test_assume_yes_uses_defaults(tmp_path, monkeypatch):
    session_dir = tmp_path / "session"
    session_dir.mkdir()

    dmd1 = session_dir / "acquisition_bar_DMD1.meta"
    dmd2 = session_dir / "acquisition_bar_DMD2.meta"
    _touch(dmd1)
    _touch(dmd2)

    # No prompting should occur under assume_yes.
    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("input called")))

    params = {
        "output_session_folder": str(session_dir),
        "assume_yes": True,
        "validate_targeted_structure_ccf": False,
        "default_targeted_structure": "VISp",
        "default_green_channel_target": "iGluSnFR4s",
        "default_red_channel_target": "jRGECO1a",
        "default_slap2_mode": "full-field raster",
        "default_pia_depth_on_remote_focus_dmd1_um": 111,
        "default_pia_depth_on_remote_focus_dmd2_um": 222,
        "default_target_name": "FOV1",
    }

    result = slap2_meta_annotator.run(params)
    assert result == 0

    annotations = list(session_dir.rglob("*.annotation.json"))
    assert annotations

    for annotation_path in annotations:
        payload = json.loads(annotation_path.read_text(encoding="utf-8"))
        assert payload["intended_green_channel_target"] == ["iGluSnFR4s"]
        assert payload["intended_red_channel_target"] == ["jRGECO1a"]
        assert payload["slap2_mode"] == "full-field raster"
        assert payload["targeted_structure"] == "VISp"
        assert "target_name" not in payload
        assert payload["fov_index"] == 1  # parsed from default_target_name FOV1
        assert payload["neuron_id"] is None
        assert payload["pia_depth_on_remote_focus_um"] in (111, 222)


def test_assume_yes_allows_none_channel_targets(tmp_path, monkeypatch):
    session_dir = tmp_path / "session"
    session_dir.mkdir()

    _touch(session_dir / "acquisition_baz_DMD1.meta")

    # No prompting should occur under assume_yes.
    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("input called")))

    params = {
        "output_session_folder": str(session_dir),
        "assume_yes": True,
        "validate_targeted_structure_ccf": False,
        "default_targeted_structure": "VISp",
        # Intentionally omit default_green_channel_target/default_red_channel_target
        "default_slap2_mode": "full-field raster",
        "default_pia_depth_on_remote_focus_dmd1_um": 111,
        "default_target_name": "FOV1",
    }

    result = slap2_meta_annotator.run(params)
    assert result == 0

    annotations = list(session_dir.rglob("*.annotation.json"))
    assert annotations

    payload = json.loads(annotations[0].read_text(encoding="utf-8"))
    assert payload["intended_green_channel_target"] == []
    assert payload["intended_red_channel_target"] == []


def test_dynamic_annotation_schema_matches_editor(tmp_path, monkeypatch):
    """Annotator output must contain the metadata editor / ETL field set.

    Mirrors _apply_dynamic_defaults in slap2_onprem_handling's
    metadata_editor: loading an annotator-produced dynamic annotation in the
    editor must add no keys.
    """
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _touch(session_dir / "acquisition_qux_DMD1.meta")
    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("input called")))

    params = {
        "output_session_folder": str(session_dir),
        "assume_yes": True,
        "validate_targeted_structure_ccf": False,
        "user_id": "operator1",
    }
    assert slap2_meta_annotator.run(params) == 0

    payload = json.loads(
        next(session_dir.rglob("*.annotation.json")).read_text(encoding="utf-8")
    )

    editor_dynamic_fields = {
        "stage_offset": None,
        "pia_depth_on_remote_focus_um": None,
        "intended_red_channel_target": [],
        "intended_green_channel_target": [],
        "neuron_id": None,
        "fov_index": -1,
        "targeted_structure": "",
        "hwp_laser_power": -1.0,
        "slap2_mode": "",
        "acquisition_type": "",
        "operator": "operator1",
        "dendrite_planes_raster": [],
        "dendrite_planes_integration": [],
        "axon_planes_raster": [],
        "axon_planes_integration": [],
        "soma_planes_raster": [],
        "soma_planes_integration": [],
    }
    for key, expected_default in editor_dynamic_fields.items():
        assert key in payload, f"missing editor/ETL field: {key}"
        assert payload[key] == expected_default, f"{key}: {payload[key]!r}"

    # Structural bookkeeping retained.
    for key in ("original_stem", "normalized_stem", "type", "moved_files", "source_rel", "dest_dir"):
        assert key in payload
    assert "target_name" not in payload
    # No silent VISp default.
    assert payload["targeted_structure"] == ""


def test_static_annotation_schema_matches_editor(tmp_path, monkeypatch):
    """Structure files get the editor's static field set (no fov_index/
    acquisition_type/planes/slap2_mode; hwp_laser_power defaults to None)."""
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _touch(session_dir / "structure_stack_DMD1.meta")
    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("input called")))

    params = {
        "output_session_folder": str(session_dir),
        "assume_yes": True,
        "validate_targeted_structure_ccf": False,
        "default_target_name": "Neuron3",
    }
    assert slap2_meta_annotator.run(params) == 0

    payload = json.loads(
        next(session_dir.rglob("static_data/*.annotation.json")).read_text(encoding="utf-8")
    )

    for key in (
        "stage_offset",
        "pia_depth_on_remote_focus_um",
        "intended_red_channel_target",
        "intended_green_channel_target",
        "neuron_id",
        "targeted_structure",
        "hwp_laser_power",
        "operator",
    ):
        assert key in payload, f"missing editor/ETL static field: {key}"
    assert payload["hwp_laser_power"] is None
    assert payload["neuron_id"] == 3  # parsed from default_target_name Neuron3
    for absent in ("fov_index", "acquisition_type", "slap2_mode", "target_name",
                   "dendrite_planes_raster"):
        assert absent not in payload, f"unexpected field on static annotation: {absent}"


def test_ref_stack_annotation_keeps_legacy_payload(tmp_path, monkeypatch):
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _touch(session_dir / "refStack_overview_DMD1.meta")
    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("input called")))

    params = {
        "output_session_folder": str(session_dir),
        "assume_yes": True,
        "validate_targeted_structure_ccf": False,
    }
    assert slap2_meta_annotator.run(params) == 0

    payload = json.loads(
        next(session_dir.rglob("reference_stack/*.annotation.json")).read_text(encoding="utf-8")
    )
    assert payload["type"] == "ref_stack"
    assert "target_name" in payload  # legacy payload untouched
    assert "fov_index" not in payload


def test_no_hardcoded_visp_default(tmp_path, monkeypatch):
    """Without an explicit pack default, targeted_structure must be blank —
    never silently stamped with 'VISp'."""
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _touch(session_dir / "acquisition_blank_DMD1.meta")
    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("input called")))

    params = {
        "output_session_folder": str(session_dir),
        "assume_yes": True,
        "validate_targeted_structure_ccf": False,
    }
    assert slap2_meta_annotator.run(params) == 0

    payload = json.loads(
        next(session_dir.rglob("*.annotation.json")).read_text(encoding="utf-8")
    )
    assert payload["targeted_structure"] == ""
