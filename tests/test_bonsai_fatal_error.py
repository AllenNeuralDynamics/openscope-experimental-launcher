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

@pytest.mark.timeout(10)
def test_fatal_error_detection_triggers_termination(monkeypatch):
    launcher = BonsaiLauncher()
    launcher.params.update({
        "subject_id": "mouse",
        "user_id": "tester",
        "output_root_folder": ".",
        # Short timeout to ensure we do not hang test
        "process_start_timeout_sec": 5,
        "fatal_error_patterns": ["System.IO.IOException", "The port 'COM"]
    })

    # Inject dummy process
    dummy = DummyProcess([
        "System.IO.IOException: The port 'COM7' does not exist.",
        "SerialPort.Open failed"
    ])
    launcher.process = dummy

    # Start output readers (will process stderr)
    launcher._start_output_readers()

    # Allow threads to process lines
    time.sleep(0.5)

    assert launcher._fatal_error_detected is True, "Fatal error flag should be set"
    assert dummy._terminated is True, "Process should be terminated on fatal error"
    assert any("System.IO.IOException" in l for l in launcher._fatal_error_lines)

@pytest.mark.timeout(10)
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
