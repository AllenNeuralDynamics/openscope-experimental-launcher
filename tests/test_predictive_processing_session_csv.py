import json
from openscope_experimental_launcher.pre_acquisition import predictive_processing_session_csv as pp_module


def test_pre_acquisition_csv_generation(tmp_path):
    # Arrange: prepare params without external repo dependency
    session_folder = tmp_path / "output_root" / "test_mouse_session"
    session_folder.mkdir(parents=True)
    params = {
        "subject_id": "test_mouse",
        "user_id": "tester",
        "output_root_folder": str(tmp_path / "output_root"),
        "output_session_folder": str(session_folder),
        "session_type": "short_test",
        "session_seed": 123,
        "session_csv_filename": "session.csv",
    }

    param_file = tmp_path / "params.json"
    param_file.write_text(json.dumps(params))

    # Act
    exit_code = pp_module.run_pre_acquisition(str(param_file))

    # Assert
    assert exit_code == 0, "Pre-acquisition module should succeed"
    csv_path = session_folder / "session.csv"
    assert csv_path.exists(), "CSV file should be created in session folder"
    with open(csv_path, 'r') as f:
        content = f.read()
    assert "Block_Label" in content, "CSV header should be present"
    meta_path = session_folder / "session.csv.meta.json"
    assert meta_path.exists(), "Sidecar metadata JSON should be created"
    meta = json.loads(meta_path.read_text())
    assert meta["session_type"] == "short_test"
    assert meta["seed"] == 123
