import json
from pathlib import Path

import pytest

from openscope_experimental_launcher.pre_acquisition import (
    metadata_procedures_fetch,
    metadata_project_validator,
    metadata_subject_fetch,
)
from openscope_experimental_launcher.utils import metadata_api


class _DummyResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.text = text

    def json(self):
        return self._json


@pytest.fixture
def base_params(tmp_path):
    return {
        "output_session_folder": str(tmp_path),
        "metadata_service_base_url": "https://metadata.example.org",
    }


def test_metadata_subject_fetch_success(monkeypatch, base_params):
    results = {}

    def fake_get(url, params=None, headers=None, timeout=None):  # noqa: D401
        results["url"] = url
        return _DummyResponse(json_data={"subject_id": "SUBJ-1"})

    monkeypatch.setattr(metadata_api, "requests", type("R", (), {"get": staticmethod(fake_get)}))

    params = dict(base_params)
    params["subject_id"] = "SUBJ-1"

    exit_code = metadata_subject_fetch.run_pre_acquisition(params)
    assert exit_code == 0
    assert results["url"].endswith("/api/v2/subject/SUBJ-1")
    output_path = Path(base_params["output_session_folder"]) / "subject.json"
    assert json.loads(output_path.read_text(encoding="utf-8"))["subject_id"] == "SUBJ-1"


def test_metadata_subject_fetch_failure(monkeypatch, base_params):
    def fake_get(url, params=None, headers=None, timeout=None):  # noqa: D401
        return _DummyResponse(status_code=404, text="not found")

    monkeypatch.setattr(metadata_api, "requests", type("R", (), {"get": staticmethod(fake_get)}))

    params = dict(base_params)
    params["subject_id"] = "UNKNOWN"

    exit_code = metadata_subject_fetch.run_pre_acquisition(params)
    assert exit_code == 1


def test_metadata_subject_fetch_validation_warning(monkeypatch, base_params):
    payload = {"message": "validation errors"}

    def fake_get(url, params=None, headers=None, timeout=None):  # noqa: D401
        return _DummyResponse(status_code=400, json_data=payload, text=json.dumps(payload))

    monkeypatch.setattr(metadata_api, "requests", type("R", (), {"get": staticmethod(fake_get)}))

    params = dict(base_params)
    params["subject_id"] = "SUBJ-1"

    exit_code = metadata_subject_fetch.run_pre_acquisition(params)
    assert exit_code == 0
    output_path = Path(base_params["output_session_folder"]) / "subject.json"
    assert json.loads(output_path.read_text(encoding="utf-8")) == payload


def test_metadata_project_validator_success(monkeypatch, base_params):
    def fake_get(url, params=None, headers=None, timeout=None):  # noqa: D401
        return _DummyResponse(json_data=["Discovery", "Atlas"])

    monkeypatch.setattr(metadata_api, "requests", type("R", (), {"get": staticmethod(fake_get)}))

    params = dict(base_params)
    params["metadata_project_name"] = "Atlas"

    exit_code = metadata_project_validator.run_pre_acquisition(params)
    assert exit_code == 0
    output_path = Path(base_params["output_session_folder"]) / "project.json"
    assert json.loads(output_path.read_text(encoding="utf-8"))["project_name"] == "Atlas"


def test_metadata_project_validator_failure(monkeypatch, base_params):
    def fake_get(url, params=None, headers=None, timeout=None):  # noqa: D401
        return _DummyResponse(json_data=["Discovery", "Atlas"])

    monkeypatch.setattr(metadata_api, "requests", type("R", (), {"get": staticmethod(fake_get)}))

    selections = {"count": 0}

    def fake_prompt(prompt, default):  # noqa: D401
        selections["count"] += 1
        return "Unknown"

    monkeypatch.setattr(metadata_project_validator.param_utils, "get_user_input", fake_prompt)

    params = dict(base_params)
    params["metadata_project_name"] = "Unknown"

    exit_code = metadata_project_validator.run_pre_acquisition(params)
    assert exit_code == 1


def test_metadata_project_validator_validation_warning(monkeypatch, base_params):
    payload = {"detail": "validation errors"}

    def fake_get(url, params=None, headers=None, timeout=None):  # noqa: D401
        return _DummyResponse(status_code=400, json_data=payload, text=json.dumps(payload))

    monkeypatch.setattr(metadata_api, "requests", type("R", (), {"get": staticmethod(fake_get)}))

    params = dict(base_params)
    params["metadata_project_name"] = "Atlas"

    exit_code = metadata_project_validator.run_pre_acquisition(params)
    assert exit_code == 0
    output_path = Path(base_params["output_session_folder"]) / "project.json"
    record = json.loads(output_path.read_text(encoding="utf-8"))
    assert record["project_name"] == "Atlas"
    assert record["metadata_response"] == payload


def test_metadata_project_validator_prompt_selection_success(monkeypatch, base_params):
    def fake_get(url, params=None, headers=None, timeout=None):  # noqa: D401
        return _DummyResponse(json_data=["Discovery", "Atlas"])

    monkeypatch.setattr(metadata_api, "requests", type("R", (), {"get": staticmethod(fake_get)}))

    entries = iter(["Discovery"])

    def fake_prompt(prompt, default):  # noqa: D401
        try:
            return next(entries)
        except StopIteration:
            return default

    monkeypatch.setattr(metadata_project_validator.param_utils, "get_user_input", fake_prompt)

    params = dict(base_params)
    params["metadata_project_name"] = "Unknown"

    exit_code = metadata_project_validator.run_pre_acquisition(params)
    assert exit_code == 0
    output_path = Path(base_params["output_session_folder"]) / "project.json"
    assert json.loads(output_path.read_text(encoding="utf-8"))["project_name"] == "Discovery"


def test_metadata_procedures_fetch_success(monkeypatch, base_params):
    captured = {}

    def fake_get(url, params=None, headers=None, timeout=None):  # noqa: D401
        captured["timeout"] = timeout
        return _DummyResponse(json_data=[{"id": 1}])

    monkeypatch.setattr(metadata_api, "requests", type("R", (), {"get": staticmethod(fake_get)}))

    params = dict(base_params)
    params["subject_id"] = "SUBJ-2"

    exit_code = metadata_procedures_fetch.run_pre_acquisition(params)
    assert exit_code == 0
    assert captured["timeout"] == pytest.approx(45.0)
    output_path = Path(base_params["output_session_folder"]) / "procedures.json"
    assert json.loads(output_path.read_text(encoding="utf-8"))[0]["id"] == 1


def test_metadata_procedures_fetch_failure(monkeypatch, base_params):
    def fake_get(url, params=None, headers=None, timeout=None):  # noqa: D401
        return _DummyResponse(status_code=404, text="missing")

    monkeypatch.setattr(metadata_api, "requests", type("R", (), {"get": staticmethod(fake_get)}))

    params = dict(base_params)
    params["subject_id"] = "SUBJ-404"

    exit_code = metadata_procedures_fetch.run_pre_acquisition(params)
    assert exit_code == 1


def test_metadata_procedures_fetch_validation_warning(monkeypatch, base_params):
    payload = [{"id": 2}]

    def fake_get(url, params=None, headers=None, timeout=None):  # noqa: D401
        return _DummyResponse(status_code=400, json_data=payload, text=json.dumps(payload))

    monkeypatch.setattr(metadata_api, "requests", type("R", (), {"get": staticmethod(fake_get)}))

    params = dict(base_params)
    params["subject_id"] = "SUBJ-2"

    exit_code = metadata_procedures_fetch.run_pre_acquisition(params)
    assert exit_code == 0
    output_path = Path(base_params["output_session_folder"]) / "procedures.json"
    assert json.loads(output_path.read_text(encoding="utf-8")) == payload


def test_metadata_procedures_fetch_timeout_override(monkeypatch, base_params):
    captured = {}

    def fake_get(url, params=None, headers=None, timeout=None):  # noqa: D401
        captured["timeout"] = timeout
        return _DummyResponse(json_data=[{"id": 3}])

    monkeypatch.setattr(metadata_api, "requests", type("R", (), {"get": staticmethod(fake_get)}))

    params = dict(base_params)
    params["subject_id"] = "SUBJ-3"
    params["metadata_procedures_timeout"] = 25

    exit_code = metadata_procedures_fetch.run_pre_acquisition(params)
    assert exit_code == 0
    assert captured["timeout"] == 25
