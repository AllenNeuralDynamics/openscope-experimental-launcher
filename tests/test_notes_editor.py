"""Tests for the shared experiment-notes editor helpers."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

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
    monkeypatch.setattr(notes_editor, "try_close_pid", lambda pid, **kw: closed.append(pid))
    # Pretend PID 999 is alive and running the expected editor.
    monkeypatch.setattr(notes_editor, "_query_image_name", lambda pid: notes_editor.DEFAULT_EDITOR_IMAGE)
    assert notes_editor.close_notes_editor(notes) is True
    assert closed == [999]


def test_close_notes_editor_no_pid_is_noop(tmp_path, monkeypatch):
    notes = tmp_path / "experiment_notes.txt"
    notes.write_text("no pid here\n", encoding="utf-8")
    closed: list[int] = []
    monkeypatch.setattr(notes_editor, "try_close_pid", lambda pid, **kw: closed.append(pid))
    assert notes_editor.close_notes_editor(notes) is False
    assert closed == []


def test_expected_image_from_command():
    assert notes_editor.expected_image_from_command("notepad.exe") == "notepad.exe"
    assert notes_editor.expected_image_from_command(r"C:\Tools\Notepad++\notepad++.exe") == "notepad++.exe"
    assert notes_editor.expected_image_from_command(["code.exe", "--wait"]) == "code.exe"
    # Garbage falls back to the safe default rather than disabling the check.
    assert notes_editor.expected_image_from_command(None) == notes_editor.DEFAULT_EDITOR_IMAGE
    assert notes_editor.expected_image_from_command(123) == notes_editor.DEFAULT_EDITOR_IMAGE


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="taskkill is Windows-only")
def test_close_notes_editor_terminates_real_process(tmp_path):
    """End-to-end (Item 18.4): a real dummy process named in the notes header
    is actually terminated, and a dead/stale PID is tolerated."""
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    image = Path(sys.executable).name
    try:
        notes = tmp_path / "experiment_notes.txt"
        notes.write_text(f"# EditorPID: {proc.pid}\nnotes body\n", encoding="utf-8")

        assert notes_editor.close_notes_editor(notes, expected_image=image) is True
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pytest.fail("notes editor process was not terminated")

        # Second close on the now-dead PID must not raise; nothing is left
        # to close, so it reports False.
        assert notes_editor.close_notes_editor(notes, expected_image=image) is False
    finally:
        if proc.poll() is None:
            proc.kill()


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="tasklist is Windows-only")
def test_recycled_pid_running_other_image_is_not_killed(tmp_path):
    """A stale EditorPID now owned by a different program must NOT be killed."""
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        notes = tmp_path / "experiment_notes.txt"
        notes.write_text(f"# EditorPID: {proc.pid}\n", encoding="utf-8")

        # Default expectation is notepad.exe; the PID is running python.
        assert notes_editor.close_notes_editor(notes) is False
        assert proc.poll() is None, "unrelated process was killed by a stale PID"
    finally:
        if proc.poll() is None:
            proc.kill()


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="process scan is Windows-only")
def test_dead_recorded_pid_falls_back_to_cmdline_scan(tmp_path):
    """Windows 11 notepad hands the file to a NEW pid and the recorded one
    exits; the close must find the real editor by image + command line."""
    notes = tmp_path / "experiment_notes.txt"

    # Get a PID that is guaranteed dead (the recorded, stale EditorPID).
    stub = subprocess.Popen([sys.executable, "-c", "pass"])
    stub.wait(timeout=30)
    notes.write_text(f"# EditorPID: {stub.pid}\nnotes\n", encoding="utf-8")

    # The "real" editor: a python process with the notes path in its argv.
    editor = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)", str(notes)]
    )
    image = Path(sys.executable).name
    try:
        assert notes_editor.close_notes_editor(notes, expected_image=image) is True
        try:
            editor.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pytest.fail("editor process found by cmdline scan was not terminated")
    finally:
        if editor.poll() is None:
            editor.kill()
