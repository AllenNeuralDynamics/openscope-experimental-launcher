import json
import logging
import socket
import threading
import time

from openscope_experimental_launcher.launchers.base_launcher import BaseLauncher
from openscope_experimental_launcher.utils import session_sync as session_sync_utils


def _reserve_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _run_in_thread(target, name, results):
    def runner():
        try:
            results[name] = target()
        except Exception as exc:  # pragma: no cover - captured for assertion
            results[name] = exc

    thread = threading.Thread(target=runner, name=name, daemon=True)
    thread.start()
    return thread


def test_session_sync_master_slave_handshake(tmp_path):
    port = _reserve_port()
    shared_session = "synced-session"

    master_params = {
        "session_sync_bind_host": "127.0.0.1",
        "session_sync_port": port,
        "session_sync_expected_slaves": 2,
        "session_sync_timeout_sec": 10,
        "session_sync_ack_timeout_sec": 5,
        "session_sync_session_name": shared_session,
        "session_sync_node_name": "master-node",
        "subject_id": "mouse",
    }

    results = {}
    master_thread = _run_in_thread(
        lambda: session_sync_utils.master_sync(
            dict(master_params), logging.getLogger(__name__), shared_session
        ),
        "session-sync-master",
        results,
    )

    time.sleep(0.2)

    slave_threads = []
    for slot in range(2):
        slave_params = {
            "session_sync_master_host": "127.0.0.1",
            "session_sync_port": port,
            "session_sync_timeout_sec": 10,
            "session_sync_ack_timeout_sec": 5,
            "session_sync_retry_delay_sec": 0.1,
            "session_sync_node_name": f"slave-{slot}",
            "subject_id": "mouse",
        }
        slave_threads.append(
            _run_in_thread(
                lambda p=slave_params: session_sync_utils.slave_sync(
                    p, logging.getLogger(__name__)
                ),
                f"session-sync-slave-{slot}",
                results,
            )
        )

    for thread in slave_threads:
        thread.join(timeout=10)
    master_thread.join(timeout=10)

    assert results["session-sync-master"] == shared_session
    assert results["session-sync-slave-0"] == shared_session
    assert results["session-sync-slave-1"] == shared_session


def _write_rig_config(path, output_dir):
    content = f'rig_id = "rig-test"\noutput_root_folder = "{output_dir}"\n'
    path.write_text(content)


def _write_param_file(path, data):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle)


def test_base_launcher_session_sync_master(monkeypatch, tmp_path):
    rig_cfg = tmp_path / "rig.toml"
    output_root = (tmp_path / "data").as_posix()
    _write_rig_config(rig_cfg, output_root)

    param_file = tmp_path / "params.json"
    _write_param_file(
        param_file,
        {
            "subject_id": "mouse",
            "user_id": "tester",
            "session_sync_role": "master",
            "session_sync_port": 41000,
            "session_sync_expected_slaves": 1,
        },
    )

    captured = {}

    def fake_master_sync(params, logger, default_name):
        captured["default"] = default_name
        return "shared-master"

    monkeypatch.setattr(session_sync_utils, "master_sync", fake_master_sync)

    launcher = BaseLauncher(param_file=str(param_file), rig_config_path=str(rig_cfg))
    launcher._maybe_synchronize_session_name()

    assert launcher.session_uuid == "shared-master"
    assert launcher.params["session_uuid"] == "shared-master"
    assert captured["default"]


def test_base_launcher_session_sync_slave(monkeypatch, tmp_path):
    rig_cfg = tmp_path / "rig.toml"
    output_root = (tmp_path / "data").as_posix()
    _write_rig_config(rig_cfg, output_root)

    param_file = tmp_path / "params.json"
    _write_param_file(
        param_file,
        {
            "subject_id": "mouse",
            "user_id": "tester",
            "session_sync_role": "slave",
            "session_sync_master_host": "localhost",
            "session_sync_port": 42000,
        },
    )

    monkeypatch.setattr(session_sync_utils, "slave_sync", lambda params, logger: "shared-slave")

    launcher = BaseLauncher(param_file=str(param_file), rig_config_path=str(rig_cfg))
    launcher._maybe_synchronize_session_name()

    assert launcher.session_uuid == "shared-slave"
    folder = launcher.determine_output_session_folder()
    assert folder.endswith("shared-slave")
