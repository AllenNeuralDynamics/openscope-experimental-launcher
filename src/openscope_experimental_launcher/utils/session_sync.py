"""Lightweight TCP coordination for sharing session names across launchers."""

from __future__ import annotations

import json
import logging
import os
import socket
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class JsonChannel:
    """Exchange newline-delimited JSON payloads on a socket."""

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self._buffer = b""

    def send(self, payload: Dict[str, Any]) -> None:
        message = json.dumps(payload, separators=(",", ":")) + "\n"
        self.sock.sendall(message.encode("utf-8"))

    def receive(self, timeout: float) -> Dict[str, Any]:
        if timeout <= 0:
            raise TimeoutError("JsonChannel.receive timeout must be positive")
        self.sock.settimeout(timeout)
        while b"\n" not in self._buffer:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("Socket closed while waiting for data")
            self._buffer += chunk
        line, remainder = self._buffer.split(b"\n", 1)
        self._buffer = remainder
        return json.loads(line.decode("utf-8"))

    def close(self) -> None:
        try:
            self.sock.close()
        except Exception:
            pass


@dataclass
class MasterConfig:
    bind_host: str
    port: int
    expected_slaves: int
    timeout: float
    ack_timeout: float
    key_param: str
    explicit_key: Optional[str]
    name_param: Optional[str]
    explicit_name: Optional[str]
    node_name: str


@dataclass
class SlaveConfig:
    master_host: str
    port: int
    timeout: float
    ack_timeout: float
    retry_delay: float
    key_param: str
    explicit_key: Optional[str]
    node_name: str


def master_sync(
    params: Dict[str, Any],
    logger: logging.Logger,
    default_session_name: Optional[str] = None,
) -> str:
    """Run the master side of the session sync protocol."""

    config = _extract_master_config(params)
    session_key = _resolve_session_key(params, config.key_param, config.explicit_key)
    session_name = _resolve_session_name(
        params,
        explicit_value=config.explicit_name,
        name_param=config.name_param,
        fallback=default_session_name,
    )
    if not session_name:
        raise ValueError("session_sync master requires a session name or fallback generator")

    logger.info(
        "Session sync master (%s) using key '%s' and session '%s'",
        config.node_name,
        session_key,
        session_name,
    )

    channels = _await_slaves(config, session_key, logger)
    try:
        _broadcast_session_name(channels, session_key, session_name, config, logger)
    finally:
        for entry in channels:
            entry["channel"].close()

    return session_name


def slave_sync(params: Dict[str, Any], logger: logging.Logger) -> str:
    """Run the slave side of the session sync protocol."""

    config = _extract_slave_config(params)
    session_key = _resolve_session_key(params, config.key_param, config.explicit_key)
    logger.info(
        "Session sync slave (%s) connecting to %s:%d with key '%s'",
        config.node_name,
        config.master_host,
        config.port,
        session_key,
    )

    channel = _connect_with_retry(config, logger)
    if channel is None:
        raise TimeoutError("Unable to connect to session sync master before timeout")

    try:
        channel.send(
            {
                "session_key": session_key,
                "state": "ready",
                "role": "slave",
                "node_name": config.node_name,
            }
        )

        announcement = channel.receive(config.ack_timeout)
        if announcement.get("status") != "announce":
            raise RuntimeError("Session sync master returned unexpected payload")
        if announcement.get("session_key") != session_key:
            raise RuntimeError("Session sync master announced mismatched session key")

        session_name = announcement.get("session_name")
        if not session_name:
            raise RuntimeError("Session sync master did not provide a session name")

        channel.send(
            {
                "status": "ack",
                "session_name": session_name,
                "node_name": config.node_name,
            }
        )

        completion = channel.receive(config.ack_timeout)
        if completion.get("status") != "complete":
            raise RuntimeError("Session sync master did not send completion signal")

        logger.info(
            "Session sync slave (%s) adopted session '%s'",
            config.node_name,
            session_name,
        )
        return str(session_name)
    finally:
        channel.close()


def _resolve_session_key(params: Dict[str, Any], key_param: str, explicit: Optional[str]) -> str:
    if explicit:
        return str(explicit)
    candidate = params.get(key_param)
    if not candidate:
        raise ValueError(f"Missing session key parameter '{key_param}' for session sync")
    return str(candidate)


def _resolve_session_name(
    params: Dict[str, Any],
    explicit_value: Optional[str],
    name_param: Optional[str],
    fallback: Optional[str],
) -> Optional[str]:
    if explicit_value:
        return str(explicit_value)
    if name_param and params.get(name_param):
        return str(params[name_param])
    if fallback:
        return str(fallback)
    folder = params.get("output_session_folder")
    if folder:
        return os.path.basename(os.path.abspath(str(folder)))
    candidate = params.get("session_uuid") or params.get("subject_id")
    if candidate:
        return str(candidate)
    return None


def _extract_master_config(params: Dict[str, Any]) -> MasterConfig:
    port = params.get("session_sync_port")
    expected = params.get("session_sync_expected_slaves")
    if not port:
        raise ValueError("session_sync_port must be provided for session sync master")
    if not expected:
        raise ValueError("session_sync_expected_slaves must be provided for session sync master")
    timeout = float(params.get("session_sync_timeout_sec", 120.0))
    ack_timeout = float(params.get("session_sync_ack_timeout_sec", 30.0))
    if timeout <= 0 or ack_timeout <= 0:
        raise ValueError("Session sync timeouts must be positive values")

    return MasterConfig(
        bind_host=str(params.get("session_sync_bind_host", "0.0.0.0")),
        port=int(port),
        expected_slaves=int(expected),
        timeout=timeout,
        ack_timeout=ack_timeout,
        key_param=str(params.get("session_sync_key_param", "subject_id")),
        explicit_key=params.get("session_sync_session_key"),
        name_param=params.get("session_sync_name_param", "session_uuid"),
        explicit_name=params.get("session_sync_session_name"),
        node_name=str(params.get("session_sync_node_name", socket.gethostname())),
    )


def _extract_slave_config(params: Dict[str, Any]) -> SlaveConfig:
    host = params.get("session_sync_master_host")
    port = params.get("session_sync_port")
    if not host or not port:
        raise ValueError(
            "session_sync_master_host and session_sync_port must be provided for session sync slave"
        )
    timeout = float(params.get("session_sync_timeout_sec", 120.0))
    ack_timeout = float(params.get("session_sync_ack_timeout_sec", 30.0))
    retry_delay = float(params.get("session_sync_retry_delay_sec", 1.0))
    if timeout <= 0 or ack_timeout <= 0 or retry_delay <= 0:
        raise ValueError("Session sync slave timeouts/delays must be positive values")

    return SlaveConfig(
        master_host=str(host),
        port=int(port),
        timeout=timeout,
        ack_timeout=ack_timeout,
        retry_delay=retry_delay,
        key_param=str(params.get("session_sync_key_param", "subject_id")),
        explicit_key=params.get("session_sync_session_key"),
        node_name=str(params.get("session_sync_node_name", socket.gethostname())),
    )


def _await_slaves(
    config: MasterConfig,
    session_key: str,
    logger: logging.Logger,
) -> List[Dict[str, Any]]:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((config.bind_host, config.port))
    server.listen(config.expected_slaves)
    logger.info(
        "Session sync master listening on %s:%d for %d slave(s)",
        config.bind_host,
        config.port,
        config.expected_slaves,
    )

    deadline = time.time() + config.timeout
    channels: List[Dict[str, Any]] = []
    try:
        while len(channels) < config.expected_slaves:
            remaining = deadline - time.time()
            if remaining <= 0:
                raise TimeoutError(
                    f"Timed out waiting for {config.expected_slaves} session sync slave(s)"
                )
            server.settimeout(remaining)
            conn, addr = server.accept()
            channel = JsonChannel(conn)
            try:
                payload = channel.receive(config.ack_timeout)
            except Exception as err:
                logger.warning("Failed to read handshake from %s: %s", addr, err)
                channel.close()
                continue

            node_name = str(payload.get("node_name") or addr)
            if payload.get("session_key") != session_key:
                logger.warning(
                    "Session sync slave %s provided mismatched key; rejecting connection",
                    node_name,
                )
                _safe_send(channel, {"status": "error", "reason": "session_key_mismatch"})
                channel.close()
                continue

            if payload.get("state") != "ready":
                logger.warning(
                    "Session sync slave %s missing ready state; rejecting connection",
                    node_name,
                )
                _safe_send(channel, {"status": "error", "reason": "invalid_state"})
                channel.close()
                continue

            logger.info("Session sync slave %s connected from %s", node_name, addr)
            channels.append({"channel": channel, "node": node_name})
        return channels
    finally:
        server.close()


def _broadcast_session_name(
    channels: List[Dict[str, Any]],
    session_key: str,
    session_name: str,
    config: MasterConfig,
    logger: logging.Logger,
) -> None:
    announcement = {
        "status": "announce",
        "session_key": session_key,
        "session_name": session_name,
        "expected_slaves": config.expected_slaves,
        "master": config.node_name,
    }
    for entry in channels:
        entry["channel"].send(announcement)

    acknowledgements: List[str] = []
    try:
        for entry in channels:
            response = entry["channel"].receive(config.ack_timeout)
            if response.get("status") != "ack" or response.get("session_name") != session_name:
                raise RuntimeError(
                    f"Session sync slave {entry['node']} failed to acknowledge session name"
                )
            acknowledgements.append(entry["node"])
            logger.info(
                "Session sync slave %s acknowledged session '%s'",
                entry["node"],
                session_name,
            )
    except Exception as err:
        error_payload = {"status": "error", "reason": str(err)}
        for entry in channels:
            _safe_send(entry["channel"], error_payload)
        raise

    release = {"status": "complete", "session_name": session_name}
    for entry in channels:
        entry["channel"].send(release)

    logger.info(
        "Session sync master received acknowledgements from: %s",
        ", ".join(acknowledgements),
    )


def _connect_with_retry(config: SlaveConfig, logger: logging.Logger) -> Optional[JsonChannel]:
    deadline = time.time() + config.timeout
    last_error: Optional[Exception] = None
    while time.time() < deadline:
        try:
            remaining = max(deadline - time.time(), 0.1)
            sock = socket.create_connection((config.master_host, config.port), timeout=remaining)
            logger.info("Session sync slave connected to master")
            return JsonChannel(sock)
        except Exception as err:
            last_error = err
            logger.debug("Session sync slave connection attempt failed: %s", err)
            sleep_time = min(config.retry_delay, max(deadline - time.time(), 0.1))
            time.sleep(sleep_time)
    if last_error:
        logger.error("Session sync slave failed to connect: %s", last_error)
    return None


def _safe_send(channel: JsonChannel, payload: Dict[str, Any]) -> None:
    try:
        channel.send(payload)
    except Exception:
        pass
