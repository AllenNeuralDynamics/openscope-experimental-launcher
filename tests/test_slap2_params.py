import json
import os
from pathlib import Path
from unittest.mock import patch

from openscope_experimental_launcher.interfaces import matlab_interface
from openscope_experimental_launcher.launchers.base_launcher import BaseLauncher
from openscope_experimental_launcher.utils import git_manager

SLAP2_PARAMS = Path(__file__).resolve().parents[1] / "params" / "matlab_slap2.json"


def _load_slap2_launcher(tmp_path):
    params = json.loads(SLAP2_PARAMS.read_text())
    params.update({"subject_id": "mouse1", "user_id": "tester"})
    param_json = tmp_path / "params.json"
    param_json.write_text(json.dumps(params))
    # loading runs the same schema validation as selecting the pack on the rig
    with patch("openscope_experimental_launcher.utils.rig_config.get_rig_config", return_value={"rig_id": "test_rig"}):
        launcher = BaseLauncher(param_file=str(param_json))
    launcher._expand_parameter_placeholders(launcher.params)  # as run() does before launching
    return launcher


def test_slap2_giant_path_matches_pinned_repository(tmp_path):
    launcher = _load_slap2_launcher(tmp_path)
    params = launcher.params

    assert params["repository_url"].endswith("/GIAnT-MATLAB.git")
    assert len(params["repository_commit_hash"]) == 40  # pinned to a full commit, not a branch

    giant_path = params["script_parameters"]["giant_path"]
    assert os.path.normpath(giant_path) == os.path.normpath(git_manager.get_repository_path(params))


def test_slap2_annotation_args_forwarded_to_matlab(tmp_path):
    launcher = _load_slap2_launcher(tmp_path)
    params = launcher.params

    args = matlab_interface._build_entrypoint_args(params, str(tmp_path), "slap2_launcher")

    assert args[:2] == ["execute", str(tmp_path)]
    pairs = dict(zip(args[2::2], args[3::2]))
    assert pairs["post_acquisition_annotation"] is True
    assert pairs["giant_path"] == params["script_parameters"]["giant_path"]
    assert "{" not in pairs["giant_path"]
