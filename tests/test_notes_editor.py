"""Tests for the shared experiment-notes editor helpers."""
from __future__ import annotations

from openscope_experimental_launcher.utils import notes_editor


def test_extract_editor_pid(tmp_path):
    notes = tmp_path / "experiment_notes.txt"
    notes.write_text("header\n# EditorPID: 1234\nbody\n", encoding="utf-8")
    assert notes_editor.extract_editor_pid(notes) == 1234


def test_extract_editor_pid_missing_file(tmp_path):
    assert notes_editor.extract_editor_pid(tmp_path / "nope.txt") is None


def test_extract_editor_pid_no_pid_line(tmp_path):
    notes = tmp_path / "experiment_notes.txt"
    notes.write_text("just notes\n", encoding="utf-8")
    assert notes_editor.extract_editor_pid(notes) is None


def test_extract_editor_pid_malformed(tmp_path):
    notes = tmp_path / "experiment_notes.txt"
    notes.write_text("# EditorPID: not-a-number\n", encoding="utf-8")
    assert notes_editor.extract_editor_pid(notes) is None


def test_close_notes_editor_attempts_close(tmp_path, monkeypatch):
    notes = tmp_path / "experiment_notes.txt"
    notes.write_text("# EditorPID: 999\n", encoding="utf-8")
    closed: list[int] = []
    monkeypatch.setattr(notes_editor, "try_close_pid", closed.append)
    assert notes_editor.close_notes_editor(notes) is True
    assert closed == [999]


def test_close_notes_editor_no_pid_is_noop(tmp_path, monkeypatch):
    notes = tmp_path / "experiment_notes.txt"
    notes.write_text("no pid here\n", encoding="utf-8")
    closed: list[int] = []
    monkeypatch.setattr(notes_editor, "try_close_pid", closed.append)
    assert notes_editor.close_notes_editor(notes) is False
    assert closed == []
