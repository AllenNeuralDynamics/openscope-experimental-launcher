import builtins

from openscope_experimental_launcher.pre_acquisition import disk_space_check


def test_disk_space_check_passes_when_enough_space(monkeypatch, tmp_path):
    def fake_disk_usage(_path):
        # total, used, free
        return (1000, 100, 900)

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
        return (1000, 950, 50)

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
        return (1000, 950, 50)

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
