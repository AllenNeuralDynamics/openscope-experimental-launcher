import builtins
from types import SimpleNamespace

from openscope_experimental_launcher.pre_acquisition import disk_space_check


def test_disk_space_check_passes_when_enough_space(monkeypatch, tmp_path):
    def fake_disk_usage(_path):
        # total, used, free
        return SimpleNamespace(total=1000, used=100, free=900)

    monkeypatch.setattr(disk_space_check.shutil, "disk_usage", fake_disk_usage)

    exit_code = disk_space_check.run_pre_acquisition(
        {
            "output_session_folder": str(tmp_path),
            "required_free_gb": 0.0000006,
        }
    )
    assert exit_code == 0


def test_disk_space_check_fails_when_not_enough_space(monkeypatch, tmp_path):
    def fake_disk_usage(_path):
        return SimpleNamespace(total=1000, used=950, free=50)

    monkeypatch.setattr(disk_space_check.shutil, "disk_usage", fake_disk_usage)

    exit_code = disk_space_check.run_pre_acquisition(
        {
            "output_session_folder": str(tmp_path),
            "required_free_gb": 0.000001,
        }
    )
    assert exit_code == 1


def test_disk_space_check_can_be_overridden(monkeypatch, tmp_path):
    def fake_disk_usage(_path):
        return SimpleNamespace(total=1000, used=950, free=50)

    def fake_input(_prompt: str):
        return "y"

    monkeypatch.setattr(disk_space_check.shutil, "disk_usage", fake_disk_usage)
    monkeypatch.setattr(builtins, "input", fake_input)

    exit_code = disk_space_check.run_pre_acquisition(
        {
            "output_session_folder": str(tmp_path),
            "required_free_gb": 0.000001,
            "allow_override": True,
        }
    )
    assert exit_code == 0


def test_disk_space_check_retries_once_after_prompt(monkeypatch, tmp_path):
    calls = {"n": 0}

    def fake_disk_usage(_path):
        calls["n"] += 1
        # First call: low free space. Second call: enough free space.
        if calls["n"] == 1:
            return SimpleNamespace(total=1000, used=950, free=50)
        return SimpleNamespace(total=1000, used=100, free=900)

    def fake_input(_prompt: str):
        # Simulate operator pressing Enter to trigger re-check.
        return ""

    monkeypatch.setattr(disk_space_check.shutil, "disk_usage", fake_disk_usage)
    monkeypatch.setattr(builtins, "input", fake_input)

    exit_code = disk_space_check.run_pre_acquisition(
        {
            "output_session_folder": str(tmp_path),
            "required_free_gb": 0.0000006,
            "allow_override": False,
            "prompt_to_free_space": True,
        }
    )
    assert exit_code == 0
