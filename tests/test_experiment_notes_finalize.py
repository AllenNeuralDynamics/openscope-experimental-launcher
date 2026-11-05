"""Tests for experiment_notes_finalize's manifest behavior.

The pack may run finalize BEFORE the annotator (operator confirms notes prior
to the metadata GUI), so finalize must never create the routing manifest —
a manifest containing only the notes would gate the archiver's network copy
down to nothing if the annotator later failed.
"""
from __future__ import annotations

import json

from openscope_experimental_launcher.post_acquisition import experiment_notes_finalize as enf
from openscope_experimental_launcher.utils import param_utils


def _params(tmp_path, notes_path):
    return {
        "output_session_folder": str(tmp_path),
        "experiment_notes_filename": str(notes_path),
        "experiment_notes_autoclose_editor": False,
        "experiment_notes_preview": False,
    }


def _confirm_yes(monkeypatch):
    monkeypatch.setattr(param_utils, "get_user_input", lambda prompt, default="": "yes")


def test_no_manifest_is_not_created(tmp_path, monkeypatch):
    notes = tmp_path / "notes" / "experiment_notes.txt"
    notes.parent.mkdir(parents=True)
    notes.write_text("notes\n", encoding="utf-8")
    _confirm_yes(monkeypatch)

    assert enf.run_post_acquisition(_params(tmp_path, notes)) == 0
    assert not (tmp_path / "launcher_metadata" / "routing_manifest.json").exists()


def test_existing_manifest_gets_notes_entry(tmp_path, monkeypatch):
    notes = tmp_path / "notes" / "experiment_notes.txt"
    notes.parent.mkdir(parents=True)
    notes.write_text("notes\n", encoding="utf-8")
    manifest = tmp_path / "launcher_metadata" / "routing_manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps({"entries": [{"type": "dynamic", "files": ["dynamic_data/a.meta"]}]}),
        encoding="utf-8",
    )
    _confirm_yes(monkeypatch)

    assert enf.run_post_acquisition(_params(tmp_path, notes)) == 0
    entries = json.loads(manifest.read_text(encoding="utf-8"))["entries"]
    notes_entries = [e for e in entries if e.get("type") == "experiment_notes"]
    assert len(notes_entries) == 1
    assert notes_entries[0]["files"] == ["notes/experiment_notes.txt"]
    # The pre-existing entry survived.
    assert any(e.get("type") == "dynamic" for e in entries)
