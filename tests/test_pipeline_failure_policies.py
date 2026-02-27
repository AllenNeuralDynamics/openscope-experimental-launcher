import json
from pathlib import Path

from openscope_experimental_launcher.launchers.base_launcher import BaseLauncher


def _write_launcher_module(path: Path, *, return_code: int) -> None:
    path.write_text(
        "def run_pre_acquisition(params):\n"
        f"    return {int(return_code)}\n"
    )


def test_pre_acquisition_on_failure_abort(tmp_path, monkeypatch):
    # Create a tiny importable pre_acquisition module that fails.
    pkg_dir = tmp_path / "openscope_experimental_launcher" / "pre_acquisition"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "openscope_experimental_launcher" / "__init__.py").write_text("")
    (pkg_dir / "__init__.py").write_text("")

    _write_launcher_module(pkg_dir / "fail_module.py", return_code=1)

    # Ensure our temp package is importable.
    import sys

    sys.path.insert(0, str(tmp_path))

    params = {
        "launcher": "base",
        "repository_url": "https://example.com/repo.git",
        "repository_commit_hash": "main",
        "local_repository_path": str(tmp_path),
        "script_path": "code/stimulus-control/src/Workflow.bonsai",
        "subject_id": "mouseX",
        "user_id": "tester",
        "output_root_folder": str(tmp_path / "out"),
        "pre_acquisition_pipeline": [
            {
                "module_type": "launcher_module",
                "module_path": "fail_module",
                "on_failure": "abort",
                "module_parameters": {},
            }
        ],
    }

    param_file = tmp_path / "params.json"
    param_file.write_text(json.dumps(params))

    # Avoid cloning.
    from openscope_experimental_launcher.utils import git_manager

    monkeypatch.setattr(git_manager, "setup_repository", lambda p: True)

    launcher = BaseLauncher(param_file=str(param_file))
    session_folder = tmp_path / "out" / "mouseX_test"
    session_folder.mkdir(parents=True, exist_ok=True)
    launcher.output_session_folder = str(session_folder)
    launcher.params.update(params)
    launcher.params["output_session_folder"] = str(session_folder)

    ok = launcher.run_pre_acquisition(param_file=str(param_file))
    assert ok is False
    assert (getattr(launcher, "_stage_abort", {}) or {}).get("pre_acquisition_pipeline") is True


def test_pre_acquisition_on_failure_continue_default(tmp_path, monkeypatch):
    pkg_dir = tmp_path / "openscope_experimental_launcher" / "pre_acquisition"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "openscope_experimental_launcher" / "__init__.py").write_text("")
    (pkg_dir / "__init__.py").write_text("")

    _write_launcher_module(pkg_dir / "fail_module.py", return_code=1)

    import sys

    sys.path.insert(0, str(tmp_path))

    params = {
        "launcher": "base",
        "repository_url": "https://example.com/repo.git",
        "repository_commit_hash": "main",
        "local_repository_path": str(tmp_path),
        "script_path": "code/stimulus-control/src/Workflow.bonsai",
        "subject_id": "mouseX",
        "user_id": "tester",
        "output_root_folder": str(tmp_path / "out"),
        "pre_acquisition_pipeline": [
            {
                "module_type": "launcher_module",
                "module_path": "fail_module",
                "module_parameters": {},
            }
        ],
    }

    param_file = tmp_path / "params.json"
    param_file.write_text(json.dumps(params))

    from openscope_experimental_launcher.utils import git_manager

    monkeypatch.setattr(git_manager, "setup_repository", lambda p: True)

    launcher = BaseLauncher(param_file=str(param_file))
    session_folder = tmp_path / "out" / "mouseX_test"
    session_folder.mkdir(parents=True, exist_ok=True)
    launcher.output_session_folder = str(session_folder)
    launcher.params.update(params)
    launcher.params["output_session_folder"] = str(session_folder)

    ok = launcher.run_pre_acquisition(param_file=str(param_file))
    assert ok is False
    assert (getattr(launcher, "_stage_abort", {}) or {}).get("pre_acquisition_pipeline") is False
