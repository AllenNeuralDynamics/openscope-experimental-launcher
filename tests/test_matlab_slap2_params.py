from __future__ import annotations

import json
from pathlib import Path


def test_matlab_slap2_template_wires_required_metadata_modules():
    param_path = Path(__file__).resolve().parents[1] / "params" / "matlab_slap2.json"
    params = json.loads(param_path.read_text(encoding="utf-8"))

    pre_modules = [entry["module_path"] for entry in params["pre_acquisition_pipeline"]]
    post_modules = [entry["module_path"] for entry in params["post_acquisition_pipeline"]]

    assert "metadata_project_validator" in pre_modules
    assert "instrument_json_fetch" in pre_modules
    assert "slap2_meta_annotator" in post_modules
    assert "slap2_behavior_annotator" in post_modules
    assert "slap2_stimuli_p3_annotator" in post_modules

    archiver_entry = next(
        entry for entry in params["post_acquisition_pipeline"] if entry["module_path"] == "session_archiver"
    )
    assert archiver_entry["module_parameters"]["session_dir"] == "{output_session_folder}"
