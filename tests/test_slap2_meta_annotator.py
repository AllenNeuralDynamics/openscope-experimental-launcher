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
            # Red target: select 1
            "1",
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
    assert combined_prompts.count("Intended Green Channel Target") == 1
    assert combined_prompts.count("Intended Red Channel Target") == 1

    # Ensure mode prompt occurred once for the DMD pair.
    assert combined_prompts.count("SLAP2 Modes") == 1

    # Verify annotations exist and include the new fields.
    annotations = list(session_dir.rglob("*.annotation.json"))
    assert len(annotations) == 2

    for annotation_path in annotations:
        payload = json.loads(annotation_path.read_text(encoding="utf-8"))
        assert payload["intended_green_channel_target"]
        assert payload["intended_red_channel_target"]
        assert payload["slap2_mode"]
        assert payload["pia_depth_on_remote_focus_um"] is not None
        assert payload["target_name"]
        assert payload["targeted_structure"]


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
        assert payload["intended_green_channel_target"] == "iGluSnFR4s"
        assert payload["intended_red_channel_target"] == "jRGECO1a"
        assert payload["slap2_mode"] == "full-field raster"
        assert payload["targeted_structure"] == "VISp"
        assert payload["target_name"] == "FOV1"
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
    assert payload["intended_green_channel_target"] is None
    assert payload["intended_red_channel_target"] is None
