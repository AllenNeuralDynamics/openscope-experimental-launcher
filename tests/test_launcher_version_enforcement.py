import json
from unittest.mock import patch

import pytest

from openscope_experimental_launcher.launchers.base_launcher import BaseLauncher


def _write_params(tmp_path, payload):
    path = tmp_path / "params.json"
    path.write_text(json.dumps(payload))
    return str(path)


def test_launcher_version_missing_warns(tmp_path):
    param_file = _write_params(
        tmp_path,
        {
            "launcher": "base",
            "subject_id": "mouse123",
            "user_id": "tester",
            "script_path": "dummy.py",
        },
    )
    with patch(
        "openscope_experimental_launcher.utils.rig_config.get_rig_config",
        return_value={"rig_id": "test_rig", "output_root_folder": "C:/tmp"},
    ):
        with pytest.warns(RuntimeWarning, match=r"does not specify 'launcher_version'"):
            BaseLauncher(param_file=param_file)


def test_launcher_version_matching_allows(tmp_path):
    param_file = _write_params(
        tmp_path,
        {
            "launcher": "base",
            "launcher_version": ">=0.2,<0.3",
            "subject_id": "mouse123",
            "user_id": "tester",
            "script_path": "dummy.py",
        },
    )
    with patch(
        "openscope_experimental_launcher.launchers.base_launcher.__version__",
        "0.2.1",
    ):
        with patch(
            "openscope_experimental_launcher.utils.rig_config.get_rig_config",
            return_value={"rig_id": "test_rig", "output_root_folder": "C:/tmp"},
        ):
            BaseLauncher(param_file=param_file)


def test_launcher_version_mismatch_errors(tmp_path):
    param_file = _write_params(
        tmp_path,
        {
            "launcher": "base",
            "launcher_version": "<0.1",
            "subject_id": "mouse123",
            "user_id": "tester",
            "script_path": "dummy.py",
        },
    )
    with patch(
        "openscope_experimental_launcher.launchers.base_launcher.__version__",
        "0.2.1",
    ):
        with patch(
            "openscope_experimental_launcher.utils.rig_config.get_rig_config",
            return_value={"rig_id": "test_rig", "output_root_folder": "C:/tmp"},
        ):
            with pytest.raises(RuntimeError, match=r"requires launcher_version"):
                BaseLauncher(param_file=param_file)
