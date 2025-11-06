import json
import os
import shutil
from pathlib import Path

from openscope_experimental_launcher.launchers.base_launcher import BaseLauncher


def _make_stub_repo(root: Path):
    repo_name = "stub_repo"
    repo_dir = root / repo_name / "code" / "stimulus-control" / "src" / "Mindscope"
    repo_dir.mkdir(parents=True, exist_ok=True)
    gen_path = repo_dir / "generate_experiment_csv.py"
    gen_path.write_text(
        "def generate_single_session_csv(session_type, output_path, seed=None):\n"
        "    with open(output_path, 'w') as f: f.write(f'session_type,{session_type},seed,{seed}')\n"
        "    return True\n"
    )
    return repo_name


def test_repo_module_pre_acquisition(tmp_path, monkeypatch):
    # Create stub repo with generator
    repo_name = _make_stub_repo(tmp_path)
    local_repo_root = tmp_path
    # Create params JSON referencing stub repo
    params = {
        "launcher": "base",
        "repository_url": f"https://example.com/{repo_name}.git",
        "repository_commit_hash": "main",
        "local_repository_path": str(local_repo_root),
        "script_path": "code/stimulus-control/src/Workflow.bonsai",  # arbitrary
        "subject_id": "mouseX",
        "user_id": "tester",
        "output_root_folder": str(tmp_path / "out"),
        "pre_acquisition_pipeline": [
            {
                "type": "repo_module",
                "repo_relative_path": "code/stimulus-control/src/Mindscope/generate_experiment_csv.py",
                "function": "generate_single_session_csv",
                "kwargs": {
                    "session_type": "short_test",
                    "seed": 123,
                    "output_filename": "session.csv"
                }
            }
        ]
    }
    param_file = tmp_path / "params.json"
    param_file.write_text(json.dumps(params))

    # Monkeypatch git_manager.setup_repository to bypass actual cloning
    from openscope_experimental_launcher.utils import git_manager
    def _fake_setup(p):
        return True
    monkeypatch.setattr(git_manager, "setup_repository", _fake_setup)

    launcher = BaseLauncher(param_file=str(param_file))
    # Manually set output session folder (bypass determine_output_session_folder for simplicity)
    session_folder = tmp_path / "out" / "mouseX_test"
    session_folder.mkdir(parents=True, exist_ok=True)
    launcher.output_session_folder = str(session_folder)
    params["output_session_folder"] = str(session_folder)
    # Overwrite processed parameters inside launcher
    launcher.params.update(params)

    success = launcher.run_pre_acquisition(param_file=str(param_file))
    assert success, "Pre-acquisition pipeline should succeed"
    csv_path = session_folder / "session.csv"
    assert csv_path.exists(), "Session CSV should be created by repo_module"
    content = csv_path.read_text()
    assert "short_test" in content and "123" in content
