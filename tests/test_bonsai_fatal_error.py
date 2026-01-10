"""Tests for fatal error detection and timeout logic in BaseLauncher when using BonsaiLauncher."""

import time
import pytest
from unittest.mock import Mock

from openscope_experimental_launcher.launchers.bonsai_launcher import BonsaiLauncher

class DummyStream:
    def __init__(self, lines):
        self._lines = list(lines)
    def readline(self):
        if not self._lines:
            return b''
        # Return bytes to exercise decode path
        return (self._lines.pop(0) + "\n").encode('utf-8')
    def close(self):
        pass

class DummyProcess:
    def __init__(self, stderr_lines):
        self._poll = None
        self.stdout = DummyStream([])
        self.stderr = DummyStream(stderr_lines)
        self._terminated = False
        self.pid = 9999
        self.returncode = None
    def poll(self):
        return self.returncode
    def terminate(self):
        self._terminated = True
        self.returncode = 1
    def wait(self, timeout=None):
        # Immediately set returncode if terminated
        if self._terminated and self.returncode is None:
            self.returncode = 1
        return self.returncode

def test_timeout_terminates_process(monkeypatch):
    launcher = BonsaiLauncher()
    launcher.params.update({
        "subject_id": "mouse",
        "user_id": "tester",
        "output_root_folder": ".",
        "process_start_timeout_sec": 1,  # very short
        "fatal_error_patterns": []
    })
    # Process that never exits unless terminated
    class HangingProcess(DummyProcess):
        def __init__(self):
            super().__init__(stderr_lines=[])
        def wait(self, timeout=None):
            # Simulate hang by sleeping longer than timeout
            time.sleep(timeout or 0.1)
            return self.returncode
    proc = HangingProcess()
    launcher.process = proc
    # Run monitor which should timeout and terminate
    launcher._monitor_process()
    assert proc._terminated is True, "Process should be terminated after timeout"


def test_bonsai_retries_then_succeeds(monkeypatch):
    launcher = BonsaiLauncher()
    launcher.params.update({
        "subject_id": "mouse",
        "user_id": "tester",
        "output_root_folder": ".",
        "bonsai_max_retries": 2,
        "bonsai_retry_delay_sec": 0,
    })

    # Always agree to retry.
    monkeypatch.setattr(
        "openscope_experimental_launcher.utils.param_utils.get_user_input",
        lambda *a, **k: "y",
    )

    # Fail twice, then succeed.
    attempts = {"n": 0}

    class ImmediateExit(DummyProcess):
        def __init__(self, rc, stderr_lines=None):
            super().__init__(stderr_lines=stderr_lines or [])
            self.returncode = rc

    def fake_create_process():
        attempts["n"] += 1
        if attempts["n"] < 3:
            return ImmediateExit(1, stderr_lines=["hardware missing"])
        return ImmediateExit(0, stderr_lines=[])

    monkeypatch.setattr(launcher, "create_process", fake_create_process)

    assert launcher.start_experiment() is True
    assert attempts["n"] == 3
