import json
import os
from pathlib import Path

import pytest

from openscope_experimental_launcher.launchers.base_launcher import BaseLauncher
from openscope_experimental_launcher.utils import github_issue_reporter


class _FakeResponse:
    def __init__(self, status_code=201, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text
        self.content = json.dumps(self._payload).encode("utf-8")

    def json(self):
        return self._payload


def test_no_token_does_not_raise(tmp_path, monkeypatch):
    """If enabled but token missing, launcher should not crash further."""

    class CrashingLauncher(BaseLauncher):
        def start_experiment(self):
            raise RuntimeError("Simulated crash")

    launcher = CrashingLauncher()
    launcher.output_session_folder = str(tmp_path)
    launcher.rig_config = {"rig_id": "test_rig"}
    launcher.params["github_issue"] = {
        "enabled": True,
        "repo": "AllenNeuralDynamics/openscope-experimental-launcher",
        "token_env": "TEST_MISSING_TOKEN",
    }

    # Avoid touching git / other side effects
    monkeypatch.setattr(
        "openscope_experimental_launcher.launchers.base_launcher.git_manager.setup_repository",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(launcher, "determine_output_session_folder", lambda: str(tmp_path))
    monkeypatch.setattr(launcher, "setup_continuous_logging", lambda *_a, **_k: None)
    monkeypatch.setattr(launcher, "save_launcher_metadata", lambda *_a, **_k: None)
    monkeypatch.setattr(launcher, "stop", lambda *_a, **_k: None)

    # Should return False and still write debug_state.json
    assert launcher.run() is False
    assert (tmp_path / "launcher_metadata" / "debug_state.json").exists()


def test_creates_issue_and_updates_debug_state(tmp_path, monkeypatch):
    class CrashingLauncher(BaseLauncher):
        def start_experiment(self):
            raise RuntimeError("Simulated crash")

    launcher = CrashingLauncher()
    launcher.output_session_folder = str(tmp_path)
    launcher.rig_config = {"rig_id": "test_rig"}
    launcher.session_uuid = "uuid-123"

    launcher.params["github_issue"] = {
        "enabled": True,
        "repo": "AllenNeuralDynamics/openscope-experimental-launcher",
        "token_env": "TEST_GITHUB_TOKEN",
        "labels": ["auto-report"],
        "max_output_lines": 5,
    }
    monkeypatch.setenv("TEST_GITHUB_TOKEN", "ghp_FAKE")

    def fake_post(url, headers=None, json=None, timeout=None):
        assert url.endswith("/repos/AllenNeuralDynamics/openscope-experimental-launcher/issues")
        assert headers and "Authorization" in headers
        assert json and "title" in json and "body" in json
        return _FakeResponse(
            201,
            payload={"html_url": "https://github.com/x/y/issues/1", "number": 1},
        )

    monkeypatch.setattr(
        "openscope_experimental_launcher.utils.github_issue_reporter.requests.post",
        fake_post,
    )

    monkeypatch.setattr(
        "openscope_experimental_launcher.launchers.base_launcher.git_manager.setup_repository",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(launcher, "determine_output_session_folder", lambda: str(tmp_path))
    monkeypatch.setattr(launcher, "setup_continuous_logging", lambda *_a, **_k: None)
    monkeypatch.setattr(launcher, "save_launcher_metadata", lambda *_a, **_k: None)
    monkeypatch.setattr(launcher, "stop", lambda *_a, **_k: None)

    assert launcher.run() is False

    debug_state_path = tmp_path / "launcher_metadata" / "debug_state.json"
    assert debug_state_path.exists()

    data = json.loads(debug_state_path.read_text(encoding="utf-8"))
    assert data.get("github", {}).get("issue_url") == "https://github.com/x/y/issues/1"
    assert data.get("github", {}).get("issue_number") == 1


def test_stage_failure_creates_issue_and_includes_full_log_no_sanitization(tmp_path, monkeypatch):
    (tmp_path / "launcher_metadata").mkdir(exist_ok=True)
    (tmp_path / "launcher_metadata" / "launcher.log").write_text(
        "Subject ID: 123, User ID: bob\nSomething else\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("TEST_GITHUB_TOKEN", "ghp_FAKE")
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["payload"] = json
        return _FakeResponse(
            201,
            payload={"html_url": "https://github.com/x/y/issues/2", "number": 2},
        )

    monkeypatch.setattr(
        "openscope_experimental_launcher.utils.github_issue_reporter.requests.post",
        fake_post,
    )

    params = {
        "github_issue": {
            "enabled": True,
            "repo": "AllenNeuralDynamics/openscope-experimental-launcher",
            "token_env": "TEST_GITHUB_TOKEN",
            "report_on": ["pre_acquisition"],
            "include_subject_user": False,
            "sanitize_launcher_log": False,
            "launcher_log_mode": "full",
            "max_output_lines": 10,
        }
    }

    url = github_issue_reporter.report_stage_failure(
        params=params,
        launcher_type="bonsai",
        version="0.0.0",
        rig_id="test_rig",
        session_uuid="uuid-123",
        param_file="params.json",
        stage_kind="pre_acquisition",
        stage_name="Pre-acquisition",
        failed_steps=["some_module"],
        output_directory=str(tmp_path),
    )
    assert url == "https://github.com/x/y/issues/2"

    body = (captured.get("payload") or {}).get("body") or ""
    assert "launcher.log" in body
    assert "Subject ID:" in body
    assert "User ID:" in body
    assert "Subject ID: 123" in body
    assert "User ID: bob" in body


def test_stage_failure_can_sanitize_launcher_log_when_enabled(tmp_path, monkeypatch):
    (tmp_path / "launcher_metadata").mkdir(exist_ok=True)
    (tmp_path / "launcher_metadata" / "launcher.log").write_text(
        "Subject ID: 123, User ID: bob\nSomething else\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("TEST_GITHUB_TOKEN", "ghp_FAKE")
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["payload"] = json
        return _FakeResponse(
            201,
            payload={"html_url": "https://github.com/x/y/issues/3", "number": 3},
        )

    monkeypatch.setattr(
        "openscope_experimental_launcher.utils.github_issue_reporter.requests.post",
        fake_post,
    )

    params = {
        "github_issue": {
            "enabled": True,
            "repo": "AllenNeuralDynamics/openscope-experimental-launcher",
            "token_env": "TEST_GITHUB_TOKEN",
            "report_on": ["pre_acquisition"],
            "include_subject_user": False,
            "sanitize_launcher_log": True,
            "launcher_log_mode": "full",
            "max_output_lines": 10,
        }
    }

    url = github_issue_reporter.report_stage_failure(
        params=params,
        launcher_type="bonsai",
        version="0.0.0",
        rig_id="test_rig",
        session_uuid="uuid-123",
        param_file="params.json",
        stage_kind="pre_acquisition",
        stage_name="Pre-acquisition",
        failed_steps=["some_module"],
        output_directory=str(tmp_path),
    )
    assert url == "https://github.com/x/y/issues/3"

    body = (captured.get("payload") or {}).get("body") or ""
    assert "Subject ID: 123" not in body
    assert "User ID: bob" not in body
    assert "<redacted>" in body


def test_stage_failure_respects_report_on(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_GITHUB_TOKEN", "ghp_FAKE")

    def should_not_be_called(*_a, **_k):
        raise AssertionError("requests.post should not be called")

    monkeypatch.setattr(
        "openscope_experimental_launcher.utils.github_issue_reporter.requests.post",
        should_not_be_called,
    )

    params = {
        "github_issue": {
            "enabled": True,
            "repo": "AllenNeuralDynamics/openscope-experimental-launcher",
            "token_env": "TEST_GITHUB_TOKEN",
            "report_on": ["exception"],
        }
    }

    url = github_issue_reporter.report_stage_failure(
        params=params,
        launcher_type="bonsai",
        version="0.0.0",
        rig_id="test_rig",
        session_uuid="uuid-123",
        param_file="params.json",
        stage_kind="pre_acquisition",
        stage_name="Pre-acquisition",
        failed_steps=["some_module"],
        output_directory=str(tmp_path),
    )
    assert url is None
