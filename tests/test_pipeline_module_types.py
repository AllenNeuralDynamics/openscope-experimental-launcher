import json
import os
import types
import importlib
from pathlib import Path

from openscope_experimental_launcher.launchers.base_launcher import BaseLauncher


class DummyLauncher(BaseLauncher):
    """Subclass BaseLauncher to avoid starting processes; overrides create_process."""
    def create_process(self):  # no real acquisition
        import subprocess, sys
        return subprocess.Popen([sys.executable, '-c', 'print("dummy acquisition")'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _write_repo_script(tmp_repo: Path):
    target = tmp_repo / 'script_mod.py'
    target.write_text(
        'def run_pre_acquisition(params):\n'
        '    out = params.get("output_session_folder")\n'
        '    import os\n'
        '    if out:\n'
        '        with open(os.path.join(out, "script_module_flag.txt"), "w") as f:\n'
        '            f.write("ok")\n'
        '    return 0\n'
    )
    return target


def test_pre_acquisition_pipeline_launcher_and_script_modules(tmp_path, monkeypatch):
    # Setup faux cloned repo
    repo_root = tmp_path / 'openscope-community-predictive-processing'
    repo_root.mkdir()
    _write_repo_script(repo_root)

    # Mock user input for mouse_weight_pre_prompt (launcher module)
    monkeypatch.setattr('openscope_experimental_launcher.utils.param_utils.get_user_input', lambda *a, **k: 25.0)

    params = {
        "launcher": "base",
        "repository_url": "https://example.com/openscope-community-predictive-processing.git",
        "local_repository_path": str(tmp_path),
        "script_path": "script_mod.py",  # not actually used in this test
        "subject_id": "test_mouse",
        "user_id": "tester",
        "output_root_folder": str(tmp_path / 'out'),
        "pre_acquisition_pipeline": [
            "mouse_weight_pre_prompt",  # launcher module
            {"module_type": "script_module", "module_path": "script_mod.py", "module_parameters": {}}
        ]
    }
    param_file = tmp_path / 'params.json'
    param_file.write_text(json.dumps(params))

    launcher = DummyLauncher(param_file=str(param_file))
    # Determine session folder so modules can write
    session_folder = launcher.determine_output_session_folder()
    launcher.output_session_folder = session_folder
    params['output_session_folder'] = session_folder
    # Persist updated params with session folder for module reads
    param_file.write_text(json.dumps(params))

    assert launcher.run_pre_acquisition(param_file=str(param_file)) is True

    # Validate artifacts
    weight_file = Path(session_folder) / 'mouse_weight.csv'
    assert weight_file.exists(), 'mouse_weight_pre_prompt should create weight file'
    script_flag = Path(session_folder) / 'script_module_flag.txt'
    assert script_flag.exists(), 'script_module should create flag file'
