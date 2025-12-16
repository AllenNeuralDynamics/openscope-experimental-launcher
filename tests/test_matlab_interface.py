import queue
from types import SimpleNamespace

import pytest

from openscope_experimental_launcher.interfaces import matlab_interface


def _build_process(connect_poll_sec=0.01, engine_name="slap2"):
    process = matlab_interface.MatlabEngineProcess.__new__(
        matlab_interface.MatlabEngineProcess
    )
    process._request = SimpleNamespace(
        connect_poll_sec=connect_poll_sec,
        engine_name=engine_name,
    )
    process._stderr_queue = queue.Queue()
    process._terminated = False
    return process


def test_wait_for_engine_recovery_retries_until_available(monkeypatch):
    process = _build_process()

    attempts = {"count": 0}

    def connector():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("engine not available")
        return "engine"

    process._engine_connector = connector
    monkeypatch.setattr(matlab_interface.time, "sleep", lambda *_: None)

    engine = process._wait_for_engine_recovery()

    assert engine == "engine"
    assert attempts["count"] == 3
    # Two failures should have been reported to stderr queue
    assert process._stderr_queue.qsize() == 2


def test_wait_for_engine_recovery_honors_termination(monkeypatch):
    process = _build_process()

    def connector():
        raise RuntimeError("engine not available")

    process._engine_connector = connector

    def sleep_and_mark(_):
        process._terminated = True

    monkeypatch.setattr(matlab_interface.time, "sleep", sleep_and_mark)

    engine = process._wait_for_engine_recovery()

    assert engine is None
    assert process._stderr_queue.qsize() == 1


def test_default_entrypoint_args_inject_execute_for_slap2():
    args = matlab_interface._build_entrypoint_args({}, None, "slap2_launcher")
    assert args == ["execute"]


def test_default_entrypoint_args_skip_for_custom_entrypoint():
    args = matlab_interface._build_entrypoint_args({}, None, "custom_launcher")
    assert args == []
