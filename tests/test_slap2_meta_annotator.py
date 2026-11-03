from __future__ import annotations

import json
import sys
import types
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


def _install_fake_editor(monkeypatch, *, result=True, raise_exc=None, side_effect=None):
    """Inject a fake slap2_onprem_handling.metadata_editor into sys.modules.

    Returns the list of (asset_dir, folder_layout) calls made to run_editor.
    """
    calls: list[tuple[Path, str]] = []

    def run_editor(asset_dir, folder_layout="autodetect"):
        calls.append((Path(asset_dir), folder_layout))
        if side_effect is not None:
            side_effect(Path(asset_dir))
        if raise_exc is not None:
            raise raise_exc
        return result

    pkg = types.ModuleType("slap2_onprem_handling")
    mod = types.ModuleType("slap2_onprem_handling.metadata_editor")
    mod.run_editor = run_editor
    pkg.metadata_editor = mod
    monkeypatch.setitem(sys.modules, "slap2_onprem_handling", pkg)
    monkeypatch.setitem(sys.modules, "slap2_onprem_handling.metadata_editor", mod)
    return calls


def test_interactive_run_asks_no_metadata_questions(tmp_path, monkeypatch):
    """Phase A asks zero metadata questions: the only interactive step left
    is the classification review. Metadata entry belongs to the GUI."""
    session_dir = tmp_path / "session"
    session_dir.mkdir()

    _touch(session_dir / "acquisition_foo_DMD1.meta")
    _touch(session_dir / "acquisition_foo_DMD2.meta")
    _touch(session_dir / "acquisition_foo_DMD1.h5")
    _touch(session_dir / "acquisition_foo_DMD2.h5")

    feeder = InputFeeder(["1"])  # review step: confirm classification
    monkeypatch.setattr("builtins.input", feeder)

    params = {
        "output_session_folder": str(session_dir),
        "assume_yes": False,
        "open_gui": False,
        "user_id": "operator1",
    }
    assert slap2_meta_annotator.run(params) == 0
    assert not feeder._replies, "unexpected extra prompts consumed no replies"

    combined_prompts = "\n".join(feeder.prompts)
    for forbidden in ("structure for", "CHANNEL", "Modes", "pia", "Target name"):
        assert forbidden not in combined_prompts, f"metadata prompt leaked: {forbidden}"

    # Scaffolds exist, blank where no pack default was provided.
    annotations = list(session_dir.rglob("*.annotation.json"))
    assert len(annotations) == 2
    for annotation_path in annotations:
        payload = json.loads(annotation_path.read_text(encoding="utf-8"))
        assert payload["intended_green_channel_target"] == []
        assert payload["intended_red_channel_target"] == []
        assert payload["slap2_mode"] == ""
        assert payload["targeted_structure"] == ""
        assert payload["pia_depth_on_remote_focus_um"] is None
        assert payload["operator"] == "operator1"


def test_dmd_pair_shares_one_classification(tmp_path, monkeypatch):
    """A DMD1/DMD2 pair is classified once (one prompt for the pair)."""
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _write_meta_hdf5(session_dir / "oddstack_x_DMD1.meta", 1.0)
    _write_meta_hdf5(session_dir / "oddstack_x_DMD2.meta", 1.0)

    feeder = InputFeeder(
        [
            # classification: ONE prompt for the pair -> reference stack
            "2",
            # review: confirm
            "1",
        ]
    )
    monkeypatch.setattr("builtins.input", feeder)

    params = _base_params(session_dir, assume_yes=False, open_gui=False)
    assert slap2_meta_annotator.run(params) == 0
    combined = "\n".join(feeder.prompts)
    assert combined.count("Operator input needed") == 1
    assert len(list(session_dir.rglob("reference_stack/*.annotation.json"))) == 2


def test_review_shows_classification_and_allows_manual_override(tmp_path, monkeypatch, capsys):
    """The review step displays the automatic classification; choosing
    'reclassify' walks each file with the current type as the default."""
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _touch(session_dir / "acquisition_foo_DMD1.meta")  # auto: dynamic

    feeder = InputFeeder(
        [
            # review: choose manual reclassification
            "2",
            # per-file prompt (default 1=dynamic): override to structure
            "2",
            # review again: confirm
            "1",
        ]
    )
    monkeypatch.setattr("builtins.input", feeder)

    params = {
        "output_session_folder": str(session_dir),
        "assume_yes": False,
        "open_gui": False,
    }
    assert slap2_meta_annotator.run(params) == 0
    assert not feeder._replies

    # The summary table was shown with the automatic type.
    output = capsys.readouterr().out
    assert "Automatic classification of .meta files:" in output
    assert "dynamic" in output

    # The operator's override won: the file was archived as a structure stack.
    assert list(session_dir.rglob("static_data/*.annotation.json"))
    assert not list(session_dir.rglob("dynamic_data/*.annotation.json"))


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
    }
    assert slap2_meta_annotator.run(params) == 0

    payload = json.loads(
        next(session_dir.rglob("*.annotation.json")).read_text(encoding="utf-8")
    )
    assert payload["targeted_structure"] == ""


def _write_meta_hdf5(path: Path, enable_stack: float) -> None:
    """Write a minimal HDF5 .meta stand-in with an enableStack scalar."""
    h5py = pytest.importorskip("h5py")
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as fh:
        fh.create_dataset("enableStack", data=[enable_stack])


def _base_params(session_dir: Path, **overrides):
    params = {
        "output_session_folder": str(session_dir),
        "assume_yes": True,
    }
    params.update(overrides)
    return params


def test_content_classification_dynamic_regardless_of_name(tmp_path, monkeypatch):
    """enableStack=0 classifies as dynamic silently, whatever the stem says."""
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _write_meta_hdf5(session_dir / "mysteryname_foo_DMD1.meta", 0.0)

    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("input called")))

    assert slap2_meta_annotator.run(_base_params(session_dir)) == 0
    annotations = list(session_dir.rglob("dynamic_data/*.annotation.json"))
    assert len(annotations) == 1
    payload = json.loads(annotations[0].read_text(encoding="utf-8"))
    assert payload["type"] == "dynamic"


def test_content_classification_stack_uses_prefix(tmp_path, monkeypatch):
    """enableStack=1 + structure_/refStack_ prefix classifies silently."""
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _write_meta_hdf5(session_dir / "structure_overview_DMD1.meta", 1.0)
    _write_meta_hdf5(session_dir / "refStack_nav_DMD1.meta", 1.0)

    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("input called")))

    assert slap2_meta_annotator.run(_base_params(session_dir)) == 0
    assert list(session_dir.rglob("static_data/*.annotation.json"))
    assert list(session_dir.rglob("reference_stack/*.annotation.json"))


def test_content_classification_stack_with_unknown_name_prompts_with_context(tmp_path, monkeypatch):
    """A z-stack with an unrecognized name asks a contextual two-way question
    for EACH such acquisition — a shared name prefix does not imply a shared
    type."""
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _write_meta_hdf5(session_dir / "oddstack_a_DMD1.meta", 1.0)
    _write_meta_hdf5(session_dir / "oddstack_b_DMD1.meta", 1.0)

    feeder = InputFeeder(["1", "2"])  # structure stack, then reference stack
    monkeypatch.setattr("builtins.input", feeder)

    kwargs = dict(
        dynamic_prefixes=slap2_meta_annotator._BUILTIN_DYNAMIC_PREFIXES,
        structure_prefixes=slap2_meta_annotator._BUILTIN_STRUCTURE_PREFIXES,
        ref_stack_prefixes=slap2_meta_annotator._BUILTIN_REF_STACK_PREFIXES,
        assume_yes=False,
    )
    first = slap2_meta_annotator._classify_meta(
        session_dir / "oddstack_a_DMD1.meta", session_dir, **kwargs
    )
    second = slap2_meta_annotator._classify_meta(
        session_dir / "oddstack_b_DMD1.meta", session_dir, **kwargs
    )

    # Each acquisition was asked individually and could differ.
    assert first == slap2_meta_annotator.TYPE_STRUCTURE
    assert second == slap2_meta_annotator.TYPE_REFSTACK
    combined = "\n".join(feeder.prompts)
    # Contextual explanation, not a bare numeric prompt.
    assert "Operator input needed to classify" in combined
    assert "z-stack" in combined
    assert "static_data/" in combined
    assert combined.count("Operator input needed") == 2


def test_fallback_unknown_prefix_prompts_and_reprompts_on_invalid(tmp_path, monkeypatch):
    """Unreadable contents + unknown name: contextual prompt, invalid input
    re-prompts, and the answer is never silently defaulted to dynamic."""
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    meta = session_dir / "weird_thing_DMD1.meta"
    meta.write_bytes(b"not hdf5")

    feeder = InputFeeder(["99", "2"])  # invalid, then structure stack
    monkeypatch.setattr("builtins.input", feeder)

    result = slap2_meta_annotator._classify_meta(
        meta,
        session_dir,
        dynamic_prefixes=slap2_meta_annotator._BUILTIN_DYNAMIC_PREFIXES,
        structure_prefixes=slap2_meta_annotator._BUILTIN_STRUCTURE_PREFIXES,
        ref_stack_prefixes=slap2_meta_annotator._BUILTIN_REF_STACK_PREFIXES,
        assume_yes=False,
    )

    assert result == slap2_meta_annotator.TYPE_STRUCTURE
    combined = "\n".join(feeder.prompts)
    assert "could not be read" in combined
    assert combined.count("Select one") >= 2  # re-prompted after invalid input


def test_assume_yes_skips_unclassifiable_files(tmp_path, monkeypatch, capsys):
    """Headless runs never guess: unclassifiable files are skipped loudly and
    summarized in an unclassified-leftovers warning at the end."""
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    (session_dir / "weird_thing_DMD1.meta").write_bytes(b"not hdf5")

    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("input called")))

    assert slap2_meta_annotator.run(_base_params(session_dir)) == 0
    # File untouched, no annotation created.
    assert (session_dir / "weird_thing_DMD1.meta").exists()
    assert not list(session_dir.rglob("*.annotation.json"))
    # Session-level leftovers summary names the file and the consequence.
    output = capsys.readouterr().out
    assert "UNCLASSIFIED LEFTOVERS" in output
    assert "weird_thing_DMD1.meta" in output
    assert "not be copied" in output


def test_activity_prefix_is_known_dynamic(tmp_path, monkeypatch):
    """Canonical sessions use activity_* stems (real S3 data finding)."""
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _touch(session_dir / "activity_20251210_134942_DMD1.meta")  # not HDF5 -> prefix path

    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("input called")))

    assert slap2_meta_annotator.run(_base_params(session_dir)) == 0
    assert list(session_dir.rglob("dynamic_data/*.annotation.json"))


def test_pack_declared_prefixes_classify_silently(tmp_path, monkeypatch):
    """Projects can declare their naming convention via module parameters."""
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _touch(session_dir / "myproj_cell1_DMD1.meta")

    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("input called")))

    params = _base_params(session_dir, dynamic_stem_prefixes=["myproj_"])
    assert slap2_meta_annotator.run(params) == 0
    assert list(session_dir.rglob("dynamic_data/*.annotation.json"))


def test_group_resolves_via_readable_partner(tmp_path, monkeypatch):
    """If one DMD file of a pair is unreadable with an odd name but its
    partner's contents resolve, the pair is classified silently."""
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    # DMD1 unreadable, DMD2 a readable dynamic acquisition — same group.
    (session_dir / "odd_pair_DMD1.meta").write_bytes(b"not hdf5")
    _write_meta_hdf5(session_dir / "odd_pair_DMD2.meta", 0.0)

    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("input called")))

    assert slap2_meta_annotator.run(_base_params(session_dir)) == 0
    annotations = list(session_dir.rglob("dynamic_data/*.annotation.json"))
    assert len(annotations) == 2  # both members classified dynamic, no prompts


# ---------------------------------------------------------------------------
# Phase B: metadata editor GUI pass
# ---------------------------------------------------------------------------


def test_gui_pass_opens_editor_on_organized_session(tmp_path, monkeypatch):
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _touch(session_dir / "acquisition_foo_DMD1.meta")

    calls = _install_fake_editor(monkeypatch, result=True)
    feeder = InputFeeder(["1"])  # review confirm
    monkeypatch.setattr("builtins.input", feeder)

    params = {"output_session_folder": str(session_dir), "assume_yes": False}
    assert slap2_meta_annotator.run(params) == 0

    assert calls == [(session_dir, "rig")]


def test_gui_pass_skipped_when_assume_yes(tmp_path, monkeypatch, capsys):
    """Headless runs never open a GUI; they warn that metadata is incomplete."""
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _touch(session_dir / "acquisition_foo_DMD1.meta")

    calls = _install_fake_editor(monkeypatch)
    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("input called")))

    assert slap2_meta_annotator.run(_base_params(session_dir)) == 0
    assert calls == []
    output = capsys.readouterr().out
    assert "NOT opening the metadata editor" in output
    assert "run the SLAP2 metadata editor" in output


def test_gui_pass_disabled_by_param(tmp_path, monkeypatch):
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _touch(session_dir / "acquisition_foo_DMD1.meta")

    calls = _install_fake_editor(monkeypatch)
    feeder = InputFeeder(["1"])
    monkeypatch.setattr("builtins.input", feeder)

    params = {"output_session_folder": str(session_dir), "assume_yes": False, "open_gui": False}
    assert slap2_meta_annotator.run(params) == 0
    assert calls == []


def test_gui_pass_editor_not_installed_warns_and_succeeds(tmp_path, monkeypatch, capsys):
    """Missing [slap2] extra degrades to a loud warning, never a failure."""
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _touch(session_dir / "acquisition_foo_DMD1.meta")

    # None in sys.modules makes `import slap2_onprem_handling...` raise ImportError.
    monkeypatch.setitem(sys.modules, "slap2_onprem_handling", None)
    monkeypatch.setitem(sys.modules, "slap2_onprem_handling.metadata_editor", None)
    feeder = InputFeeder(["1"])
    monkeypatch.setattr("builtins.input", feeder)

    params = {"output_session_folder": str(session_dir), "assume_yes": False}
    assert slap2_meta_annotator.run(params) == 0
    output = capsys.readouterr().out
    assert "not installed" in output
    assert "[slap2] extra" in output


def test_gui_pass_editor_crash_never_fails_launcher(tmp_path, monkeypatch, capsys):
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _touch(session_dir / "acquisition_foo_DMD1.meta")

    calls = _install_fake_editor(monkeypatch, raise_exc=RuntimeError("no display"))
    feeder = InputFeeder(["1"])
    monkeypatch.setattr("builtins.input", feeder)

    params = {"output_session_folder": str(session_dir), "assume_yes": False}
    assert slap2_meta_annotator.run(params) == 0
    assert len(calls) == 1
    output = capsys.readouterr().out
    assert "could not run" in output
    assert "run the SLAP2 metadata editor" in output


def test_gui_pass_closed_without_saving_warns(tmp_path, monkeypatch, capsys):
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _touch(session_dir / "acquisition_foo_DMD1.meta")

    _install_fake_editor(monkeypatch, result=False)
    feeder = InputFeeder(["1"])
    monkeypatch.setattr("builtins.input", feeder)

    params = {"output_session_folder": str(session_dir), "assume_yes": False}
    assert slap2_meta_annotator.run(params) == 0
    output = capsys.readouterr().out
    assert "WITHOUT saving" in output


def test_gui_pass_empty_session_respects_open_gui_when_empty(tmp_path, monkeypatch):
    """No .meta files: GUI is skipped by default, opened with open_gui_when_empty."""
    session_dir = tmp_path / "session"
    session_dir.mkdir()

    calls = _install_fake_editor(monkeypatch)
    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("input called")))

    params = {"output_session_folder": str(session_dir), "assume_yes": False}
    assert slap2_meta_annotator.run(params) == 0
    assert calls == []

    params["open_gui_when_empty"] = True
    assert slap2_meta_annotator.run(params) == 0
    assert calls == [(session_dir, "rig")]


# ---------------------------------------------------------------------------
# Pack-param prefills
# ---------------------------------------------------------------------------


def test_stage_offset_prefills_per_type(tmp_path, monkeypatch):
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _write_meta_hdf5(session_dir / "acquisition_dyn_DMD1.meta", 0.0)
    _write_meta_hdf5(session_dir / "structure_stk_DMD1.meta", 1.0)

    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("input called")))

    params = _base_params(
        session_dir,
        default_dynamic_stage_offset=[1.5, -2.5],
        default_static_stage_offset=[3, 4],
    )
    assert slap2_meta_annotator.run(params) == 0

    dynamic_payload = json.loads(
        next(session_dir.rglob("dynamic_data/*.annotation.json")).read_text(encoding="utf-8")
    )
    static_payload = json.loads(
        next(session_dir.rglob("static_data/*.annotation.json")).read_text(encoding="utf-8")
    )
    assert dynamic_payload["stage_offset"] == [1.5, -2.5]
    assert static_payload["stage_offset"] == [3.0, 4.0]


def test_malformed_stage_offset_is_ignored(tmp_path, monkeypatch):
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _write_meta_hdf5(session_dir / "acquisition_dyn_DMD1.meta", 0.0)

    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("input called")))

    params = _base_params(session_dir, default_dynamic_stage_offset=[1, 2, 3])
    assert slap2_meta_annotator.run(params) == 0

    payload = json.loads(
        next(session_dir.rglob("dynamic_data/*.annotation.json")).read_text(encoding="utf-8")
    )
    assert payload["stage_offset"] is None


# ---------------------------------------------------------------------------
# Re-run safety
# ---------------------------------------------------------------------------


def test_colliding_normalized_stems_do_not_overwrite_annotations(tmp_path, monkeypatch):
    """Two distinct acquisitions that normalize to the same stem must yield
    two annotations — never a silent overwrite or _dup-mangled data files."""
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _write_meta_hdf5(session_dir / "mystery_foo_DMD1.meta", 0.0)
    _write_meta_hdf5(session_dir / "other_foo_DMD1.meta", 0.0)

    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("input called")))

    assert slap2_meta_annotator.run(_base_params(session_dir)) == 0

    annotations = sorted(session_dir.rglob("dynamic_data/*.annotation.json"))
    assert len(annotations) == 2
    stems = sorted(json.loads(p.read_text(encoding="utf-8"))["original_stem"] for p in annotations)
    assert stems == ["mystery_foo_DMD1", "other_foo_DMD1"]
    assert not [p for p in session_dir.rglob("*") if "_dup" in p.name]


def test_canonical_stem_is_left_unchanged(tmp_path, monkeypatch):
    """A stem already carrying the canonical prefix keeps its full name
    (token-dropping would collapse distinct acquisitions)."""
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _touch(session_dir / "acquisition_20251210_134942_DMD1.meta")

    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("input called")))

    assert slap2_meta_annotator.run(_base_params(session_dir)) == 0
    assert (session_dir / "dynamic_data" / "acquisition_20251210_134942_DMD1.meta").exists()
    payload = json.loads(
        (session_dir / "dynamic_data" / "acquisition_20251210_134942_DMD1.annotation.json")
        .read_text(encoding="utf-8")
    )
    assert payload["normalized_stem"] == "acquisition_20251210_134942_DMD1"


def test_rerun_never_renames_or_overwrites_filled_annotations(tmp_path, monkeypatch):
    """A second annotator run must not _dup-rename organized files nor
    clobber operator-entered metadata in existing annotations."""
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _write_meta_hdf5(session_dir / "acquisition_foo_DMD1.meta", 0.0)
    _touch(session_dir / "acquisition_foo_DMD1.h5")

    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("input called")))

    assert slap2_meta_annotator.run(_base_params(session_dir)) == 0

    annotation_path = next(session_dir.rglob("dynamic_data/*.annotation.json"))
    payload = json.loads(annotation_path.read_text(encoding="utf-8"))
    payload["targeted_structure"] = "VISp"  # simulate operator GUI entry
    annotation_path.write_text(json.dumps(payload), encoding="utf-8")

    files_before = sorted(p.relative_to(session_dir).as_posix() for p in session_dir.rglob("*") if p.is_file())

    assert slap2_meta_annotator.run(_base_params(session_dir)) == 0

    files_after = sorted(p.relative_to(session_dir).as_posix() for p in session_dir.rglob("*") if p.is_file())
    assert files_before == files_after
    assert not [f for f in files_after if "_dup" in f]
    payload = json.loads(annotation_path.read_text(encoding="utf-8"))
    assert payload["targeted_structure"] == "VISp"  # operator data survived


# ---------------------------------------------------------------------------
# Routing-manifest reconciliation
# ---------------------------------------------------------------------------


def _manifest_files(manifest_path: Path) -> set[str]:
    entries = json.loads(manifest_path.read_text(encoding="utf-8"))["entries"]
    files: set[str] = set()
    for entry in entries:
        files.update(entry.get("files") or [])
    return files


def test_reconcile_registers_untracked_files(tmp_path, monkeypatch):
    """Files created after the mechanical pass (rig extras, GIAnT output)
    get registered so the archiver copies them; repeat runs are idempotent."""
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _write_meta_hdf5(session_dir / "acquisition_foo_DMD1.meta", 0.0)
    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("input called")))
    assert slap2_meta_annotator.run(_base_params(session_dir)) == 0

    manifest_path = session_dir / "launcher_metadata" / "routing_manifest.json"
    _touch(session_dir / "dynamic_data" / "rigDescription.json")
    _touch(session_dir / "dynamic_data" / "rois1.json")
    _touch(session_dir / "postacq_annotations.h5")

    slap2_meta_annotator._reconcile_manifest(
        session_dir,
        manifest_path,
        scan_rel_dirs=("dynamic_data", "static_data", "dynamic_data/reference_stack"),
    )
    files = _manifest_files(manifest_path)
    assert "dynamic_data/rigDescription.json" in files
    assert "dynamic_data/rois1.json" in files
    assert "postacq_annotations.h5" in files

    # Idempotent: a second reconcile changes nothing.
    before = manifest_path.read_text(encoding="utf-8")
    slap2_meta_annotator._reconcile_manifest(
        session_dir,
        manifest_path,
        scan_rel_dirs=("dynamic_data", "static_data", "dynamic_data/reference_stack"),
    )
    assert manifest_path.read_text(encoding="utf-8") == before


def test_reconcile_never_creates_a_manifest(tmp_path):
    """No manifest means the archiver copies everything; reconciliation must
    not create one that would gate archiving down to stragglers."""
    session_dir = tmp_path / "session"
    (session_dir / "dynamic_data").mkdir(parents=True)
    _touch(session_dir / "dynamic_data" / "orphan.json")
    manifest_path = session_dir / "launcher_metadata" / "routing_manifest.json"

    slap2_meta_annotator._reconcile_manifest(
        session_dir,
        manifest_path,
        scan_rel_dirs=("dynamic_data", "static_data", "dynamic_data/reference_stack"),
    )
    assert not manifest_path.exists()


def test_gui_created_annotations_get_registered(tmp_path, monkeypatch):
    """Annotations the editor scaffolds during Phase B end up in the manifest."""
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _touch(session_dir / "acquisition_foo_DMD1.meta")

    def _editor_writes_annotation(asset_dir: Path) -> None:
        extra = asset_dir / "dynamic_data" / "editor_created.annotation.json"
        extra.write_text("{}", encoding="utf-8")

    _install_fake_editor(monkeypatch, result=True, side_effect=_editor_writes_annotation)
    feeder = InputFeeder(["1"])
    monkeypatch.setattr("builtins.input", feeder)

    params = {"output_session_folder": str(session_dir), "assume_yes": False}
    assert slap2_meta_annotator.run(params) == 0

    manifest_path = session_dir / "launcher_metadata" / "routing_manifest.json"
    assert "dynamic_data/editor_created.annotation.json" in _manifest_files(manifest_path)


# ---------------------------------------------------------------------------
# Notes-editor handoff (Item 15)
# ---------------------------------------------------------------------------


def test_archiver_honors_reconciled_manifest(tmp_path, monkeypatch):
    """End-to-end gating (Item 18.5): everything the annotator organizes or
    reconciles — including GIAnT's postacq_annotations.h5 at the session
    root — is allowed through the archiver's network gate."""
    from openscope_experimental_launcher.post_acquisition.session_archiver import SessionArchiver

    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _write_meta_hdf5(session_dir / "acquisition_foo_DMD1.meta", 0.0)
    _touch(session_dir / "acquisition_foo_DMD1.h5")
    _touch(session_dir / "postacq_annotations.h5")  # written by the MATLAB/GIAnT phase

    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("input called")))
    assert slap2_meta_annotator.run(_base_params(session_dir)) == 0

    archiver = SessionArchiver(
        session_dir,
        tmp_path / "network",
        tmp_path / "backup",
        manifest_path=tmp_path / "archive_manifest.json",
        routing_manifest_path=session_dir / "launcher_metadata" / "routing_manifest.json",
        dry_run=True,
    )
    allowed = archiver._routing_rel
    for rel in (
        "dynamic_data/acquisition_foo_DMD1.meta",
        "dynamic_data/acquisition_foo_DMD1.h5",
        "dynamic_data/acquisition_foo_DMD1.annotation.json",
        "postacq_annotations.h5",
        "launcher_metadata/routing_manifest.json",
    ):
        assert rel in allowed, f"not network-allowed: {rel}"


def test_annotator_closes_notes_editor_before_prompting(tmp_path, monkeypatch):
    from openscope_experimental_launcher.utils import notes_editor

    session_dir = tmp_path / "session"
    session_dir.mkdir()
    (session_dir / "experiment_notes.txt").write_text(
        "# EditorPID: 4242\nsome notes\n", encoding="utf-8"
    )
    _touch(session_dir / "acquisition_foo_DMD1.meta")

    closed: list[int] = []
    monkeypatch.setattr(notes_editor, "try_close_pid", closed.append)
    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("input called")))

    assert slap2_meta_annotator.run(_base_params(session_dir)) == 0
    assert closed == [4242]


def test_notes_editor_close_can_be_disabled(tmp_path, monkeypatch):
    from openscope_experimental_launcher.utils import notes_editor

    session_dir = tmp_path / "session"
    session_dir.mkdir()
    (session_dir / "experiment_notes.txt").write_text(
        "# EditorPID: 4242\n", encoding="utf-8"
    )
    _touch(session_dir / "acquisition_foo_DMD1.meta")

    closed: list[int] = []
    monkeypatch.setattr(notes_editor, "try_close_pid", closed.append)
    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("input called")))

    assert slap2_meta_annotator.run(_base_params(session_dir, close_notes_editor=False)) == 0
    assert closed == []
