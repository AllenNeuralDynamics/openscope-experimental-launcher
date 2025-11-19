from pathlib import Path

from openscope_experimental_launcher.pre_acquisition import experiment_notes_editor
from openscope_experimental_launcher.post_acquisition import experiment_notes_finalize


def _base_params(session_dir: Path) -> dict:
    return {
        "output_session_folder": str(session_dir),
        "session_uuid": "session-test",
        "experiment_notes_launch_editor": False,
    }


def test_experiment_notes_pre_creates_file(tmp_path):
    session_dir = tmp_path / "session"
    session_dir.mkdir()

    params = _base_params(session_dir)
    exit_code = experiment_notes_editor.run_pre_acquisition(params)
    assert exit_code == 0

    notes_path = session_dir / "experiment_notes.txt"
    assert notes_path.exists()
    contents = notes_path.read_text(encoding="utf-8")
    assert contents.startswith("# Experiment Notes")


def test_experiment_notes_post_prompts_for_confirmation(tmp_path, monkeypatch):
    session_dir = tmp_path / "session"
    session_dir.mkdir()

    params = _base_params(session_dir)
    pre_exit = experiment_notes_editor.run_pre_acquisition(params)
    assert pre_exit == 0

    notes_path = session_dir / "experiment_notes.txt"
    notes_path.write_text("note content", encoding="utf-8")

    captured = {}

    def fake_input(prompt: str, default: str):
        captured["prompt"] = prompt
        captured["default"] = default
        return default

    monkeypatch.setattr(experiment_notes_finalize.param_utils, "get_user_input", fake_input)

    post_exit = experiment_notes_finalize.run_post_acquisition(params)
    assert post_exit == 0
    assert notes_path.exists()
    assert captured["prompt"] == experiment_notes_finalize._DEFAULT_CONFIRM_PROMPT
    assert captured["default"] == ""
