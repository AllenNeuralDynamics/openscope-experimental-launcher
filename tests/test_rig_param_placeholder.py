import pytest
from unittest.mock import patch

from openscope_experimental_launcher.launchers.base_launcher import BaseLauncher


def test_rig_param_placeholder_expansion(tmp_path):
    rig_cfg = {"rig_id": "test_rig", "COM_port": "COM7", "RecordCameras": True}
    param_json = tmp_path / "params.json"
    param_json.write_text(
        """
        {
          "subject_id": "mouse1",
          "user_id": "tester",
          "script_parameters": {
             "PortName": "{rig_param:COM_port}",
             "RecordCameras": "{rig_param:RecordCameras}"
          }
        }
        """
    )
    with patch('openscope_experimental_launcher.utils.rig_config.get_rig_config', return_value=rig_cfg):
        launcher = BaseLauncher(param_file=str(param_json))
    sp = launcher.params['script_parameters']
    assert sp['PortName'] == 'COM7'
    # Bool placeholder should turn into string 'True' (not normalized here, Bonsai interface lowercases later)
    assert sp['RecordCameras'] == 'True'


def test_unknown_rig_param_raises(tmp_path):
    rig_cfg = {"rig_id": "test_rig"}
    param_json = tmp_path / "params.json"
    param_json.write_text(
        """
        {"subject_id": "m2", "user_id": "u2", "script_parameters": {"X": "{rig_param:missing_key}"}}
        """
    )
    with patch('openscope_experimental_launcher.utils.rig_config.get_rig_config', return_value=rig_cfg):
        with pytest.raises(RuntimeError):
            BaseLauncher(param_file=str(param_json))
