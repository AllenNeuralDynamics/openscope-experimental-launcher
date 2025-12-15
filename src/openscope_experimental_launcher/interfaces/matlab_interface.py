"""MATLAB engine integration for OpenScope experimental launchers.

This module provides helpers for connecting to a shared MATLAB engine,
invoking MATLAB entry points, and capturing MATLAB output so it can flow
through the standard launcher logging pipeline.
"""

from __future__ import annotations

import importlib
import io
import logging
import os
import queue
import subprocess
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

__all__ = [
    "MatlabLaunchRequest",
    "MatlabEngineProcess",
    "setup_matlab_environment",
    "build_launch_request",
    "connect_shared_engine",
    "start_matlab_function",
    "cleanup_engine",
]


class MatlabEngineUnavailable(RuntimeError):
    """Raised when matlab.engine cannot be imported."""


_MATLAB_ENGINE_MODULE: Optional[Any] = None


def _ensure_matlab_engine():
    """Import and cache the matlab.engine module."""

    global _MATLAB_ENGINE_MODULE
    if _MATLAB_ENGINE_MODULE is not None:
        return _MATLAB_ENGINE_MODULE

    try:  # pragma: no cover - requires MATLAB runtime
        matlab_engine = importlib.import_module("matlab.engine")
    except ImportError as exc:  # pragma: no cover - handled at runtime
        raise MatlabEngineUnavailable(
            "MATLAB Engine for Python is not installed. "
            "Install it from your MATLAB distribution to use the MATLAB launcher."
        ) from exc

    _MATLAB_ENGINE_MODULE = matlab_engine
    return matlab_engine


def setup_matlab_environment(params: Dict[str, Any]) -> bool:
    """Validate that the MATLAB Engine for Python is available."""

    try:
        _ensure_matlab_engine()
    except MatlabEngineUnavailable as exc:
        logging.error(str(exc))
        return False
    return True


@dataclass
class MatlabLaunchRequest:
    """Lightweight container describing a MATLAB engine launch request."""

    engine_name: str
    entry_point: str
    args: List[Any] = field(default_factory=list)
    nargout: int = 0
    connect_timeout_sec: float = 120.0
    connect_poll_sec: float = 1.0
    session_folder: Optional[str] = None
    keep_engine_alive: bool = True
    cancel_timeout_sec: float = 15.0
    enable_resume: bool = False
    resume_keyword: str = "resume"

    def build_call_args(self, is_resume_attempt: bool) -> List[Any]:
        """Create the MATLAB argument list for an acquisition attempt."""

        call_args = list(self.args)
        if self.enable_resume:
            call_args.extend([self.resume_keyword, bool(is_resume_attempt)])
        return call_args


def build_launch_request(params: Dict[str, Any], session_folder: Optional[str]) -> Optional[MatlabLaunchRequest]:
    """Derive a :class:`MatlabLaunchRequest` from launcher parameters."""

    if not setup_matlab_environment(params):
        return None

    engine_name = str(params.get("matlab_engine_name", "slap2_launcher"))

    entry_point: Optional[str] = params.get("matlab_entrypoint") or params.get("matlab_function")
    if not entry_point:
        script_path = params.get("script_path")
        if script_path:
            entry_point = os.path.splitext(os.path.basename(script_path))[0]

    if not entry_point:
        logging.error(
            "MATLAB entry point not provided. Set 'matlab_entrypoint' or 'matlab_function' "
            "in the parameter file."
        )
        return None

    try:
        args = _build_entrypoint_args(params, session_folder)
    except Exception as exc:
        logging.error("Invalid MATLAB entry point arguments: %s", exc)
        return None

    nargout = int(params.get("matlab_entrypoint_nargout", 0) or 0)
    timeout = float(params.get("matlab_engine_connect_timeout_sec", 120) or 0)
    poll = float(params.get("matlab_engine_connect_poll_interval_sec", 1) or 1)
    cancel_timeout = float(params.get("matlab_cancel_timeout_sec", 15) or 15)
    keep_alive = bool(params.get("matlab_keep_engine_alive", True))

    enable_resume = bool(params.get("matlab_enable_resume", True))
    resume_keyword = str(params.get("matlab_resume_keyword", "resume"))

    if enable_resume:
        resume_token = resume_keyword.lower()
        arg_tokens = [
            str(item).lower()
            for item in args
            if isinstance(item, (str, bytes))
        ]
        if resume_token in arg_tokens:
            logging.warning(
                "MATLAB entry point arguments already include the resume keyword '%s'; disabling automatic resume flag injection.",
                resume_keyword,
            )
            enable_resume = False

    request = MatlabLaunchRequest(
        engine_name=engine_name,
        entry_point=str(entry_point),
        args=args,
        nargout=nargout,
        connect_timeout_sec=max(timeout, 0.0),
        connect_poll_sec=max(poll, 0.1),
        session_folder=session_folder,
        keep_engine_alive=keep_alive,
        cancel_timeout_sec=max(cancel_timeout, 1.0),
        enable_resume=enable_resume,
        resume_keyword=resume_keyword,
    )

    return request


def _build_entrypoint_args(params: Dict[str, Any], session_folder: Optional[str]) -> List[Any]:
    """Compose the MATLAB entry-point positional arguments list."""

    raw_args = params.get("matlab_entrypoint_args", [])
    if raw_args is None:
        raw_args = []

    if isinstance(raw_args, tuple):
        raw_args = list(raw_args)

    if not isinstance(raw_args, list):
        raise TypeError("'matlab_entrypoint_args' must be a list when provided")

    args: List[Any] = list(raw_args)

    include_session = params.get("matlab_pass_session_folder", True)
    if include_session and session_folder:
        position = params.get("matlab_session_folder_position", "append")
        insertion_value = session_folder

        if isinstance(position, int):
            index = max(0, min(len(args), position))
            args.insert(index, insertion_value)
        else:
            choice = str(position).lower()
            if choice == "prepend":
                args.insert(0, insertion_value)
            elif choice == "ignore":
                pass
            else:
                args.append(insertion_value)

    kwargs = params.get("matlab_entrypoint_kwargs", {})
    if kwargs and not isinstance(kwargs, dict):
        raise TypeError("'matlab_entrypoint_kwargs' must be a dictionary when provided")

    script_parameters = params.get("script_parameters", {})
    if script_parameters and not isinstance(script_parameters, dict):
        raise TypeError("'script_parameters' must be a dictionary when launching MATLAB workflows")

    ordered_kwargs: "OrderedDict[str, Any]" = OrderedDict()

    if isinstance(script_parameters, dict):
        for key, value in script_parameters.items():
            if key is None:
                continue
            ordered_kwargs[str(key)] = value

    if isinstance(kwargs, dict):
        for key, value in kwargs.items():
            ordered_kwargs[str(key)] = value

    rig_description_path = (
        params.get("matlab_rig_description_path") or params.get("rig_description_path")
    )
    if rig_description_path and "rig_description_path" not in ordered_kwargs:
        ordered_kwargs["rig_description_path"] = str(rig_description_path)

    for key, value in ordered_kwargs.items():
        args.extend([key, value])

    return args


def connect_shared_engine(request: MatlabLaunchRequest) -> Any:
    """Attach to an already shared MATLAB engine."""

    matlab_engine = _ensure_matlab_engine()

    timeout = request.connect_timeout_sec
    poll_interval = request.connect_poll_sec
    start_time = time.time()
    attempt = 0
    last_error: Optional[Exception] = None

    while True:
        attempt += 1
        try:
            engine = matlab_engine.connect_matlab(request.engine_name)
            logging.info(
                "Connected to shared MATLAB engine '%s' after %d attempt(s)",
                request.engine_name,
                attempt,
            )
            return engine
        except matlab_engine.EngineError as exc:  # pragma: no cover - depends on MATLAB runtime
            last_error = exc
            elapsed = time.time() - start_time
            if timeout > 0 and elapsed >= timeout:
                break
            logging.info(
                "Waiting for MATLAB engine '%s' to become available (attempt %d)...",
                request.engine_name,
                attempt,
            )
            time.sleep(poll_interval)
        except Exception as exc:  # pragma: no cover - defensive
            last_error = exc
            break

    raise RuntimeError(
        f"Could not connect to MATLAB engine '{request.engine_name}': {last_error}"
    )


class _MatlabStreamSink(io.StringIO):
    """StringIO-compatible sink that forwards MATLAB output into a queue."""

    def __init__(self, target_queue: "queue.Queue[str]"):
        super().__init__()
        self._queue = target_queue
        self._buffer = ""
        self._lock = threading.Lock()
        self._closed = False

    def write(self, data: Any) -> int:  # pragma: no cover - relies on MATLAB engine callbacks
        if self._closed or data is None:
            return 0

        if not isinstance(data, str):
            try:
                data = data.decode("utf-8", errors="replace")
            except Exception:
                data = str(data)

        data = data.replace("\r\n", "\n").replace("\r", "\n")

        with self._lock:
            self._buffer += data
            while "\n" in self._buffer:
                line, self._buffer = self._buffer.split("\n", 1)
                if line:
                    self._queue.put(line.rstrip())
        super().write(data)
        # Prevent unbounded growth of the underlying buffer.
        self.seek(0)
        self.truncate(0)
        return len(data)

    def flush(self) -> None:  # pragma: no cover - relies on MATLAB engine callbacks
        with self._lock:
            if self._buffer:
                residual = self._buffer.rstrip()
                if residual:
                    self._queue.put(residual)
                self._buffer = ""
        super().flush()

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self.flush()
        super().close()


class _QueueReader:
    """File-like wrapper providing readline() over a queue."""

    def __init__(self, source_queue: "queue.Queue[Optional[str]]"):
        self._queue = source_queue
        self._closed = False

    def readline(self) -> str:
        if self._closed:
            return ""
        item = self._queue.get()
        if item is None:
            self._closed = True
            return ""
        return f"{item}\n"

    def close(self) -> None:
        self._closed = True


class MatlabEngineProcess:
    """Popen-like wrapper around a MATLAB asynchronous call with resume support."""

    def __init__(
        self,
        engine: Any,
        stdout_queue: "queue.Queue[Optional[str]]",
        stderr_queue: "queue.Queue[Optional[str]]",
        stdout_sink: _MatlabStreamSink,
        stderr_sink: _MatlabStreamSink,
        request: MatlabLaunchRequest,
        engine_connector: Callable[[], Any],
    ) -> None:
        self._stdout_queue = stdout_queue
        self._stderr_queue = stderr_queue
        self._stdout_sink = stdout_sink
        self._stderr_sink = stderr_sink
        self._request = request
        self._engine_connector = engine_connector
        self._streams_closed = False

        self.stdout = _QueueReader(stdout_queue)
        self.stderr = _QueueReader(stderr_queue)

        self.returncode: Optional[int] = None
        self.pid: Optional[int] = None  # No discrete PID for shared engine calls

        self._done = threading.Event()
        self._terminated = False
        self._attempt = 0
        self._engine: Optional[Any] = None
        self._future: Optional[Any] = None

        self._start_call(engine)

        self._monitor_thread = threading.Thread(target=self._monitor_future, daemon=True)
        self._monitor_thread.start()

    @property
    def current_engine(self) -> Optional[Any]:
        return self._engine

    @property
    def attempt_count(self) -> int:
        return self._attempt

    @property
    def resume_attempts(self) -> int:
        return max(0, self._attempt - 1)

    def _start_call(self, engine: Any) -> None:
        self._engine = engine
        self._attempt += 1
        resume_flag = self._attempt > 1
        call_args = self._request.build_call_args(resume_flag)

        phase = "Resuming" if resume_flag else "Starting"
        status_message = (
            f"{phase} MATLAB entry point '{self._request.entry_point}' (attempt {self._attempt})"
        )

        try:
            helper_info = self._initialise_helper(engine, status_message)
        except Exception as exc:
            self._attempt -= 1
            self._engine = None
            error_message = str(exc)
            logging.error(error_message)
            self._stderr_queue.put(error_message)
            raise

        try:  # pragma: no cover - relies on MATLAB runtime
            self._future = _dispatch_matlab_feval(
                engine,
                self._request.entry_point,
                call_args,
                self._request.nargout,
                self._stdout_sink,
                self._stderr_sink,
            )
        except Exception as exc:  # pragma: no cover - MATLAB runtime dependent
            self._attempt -= 1
            self._engine = None
            self._future = None
            raise RuntimeError(
                f"Failed to invoke MATLAB entry point '{self._request.entry_point}': {exc}"
            ) from exc

        logging.info(status_message)
        self._stdout_queue.put(status_message)
        self._log_helper_metadata(helper_info)

    def _initialise_helper(self, engine: Any, status_message: str) -> Optional[Any]:
        helper_info: Optional[Any] = None

        def _call_status_updater() -> None:
            if not status_message:
                return
            try:
                feval_func("slap2_launcher", "helper_set_status", status_message, nargout=0)
            except Exception:
                try:
                    escaped = status_message.replace("'", "''")
                    evaluation(
                        f"slap2_launcher('helper_set_status', '{escaped}')",
                        nargout=0,
                    )
                except Exception:
                    pass

        feval_func = getattr(engine, "feval", None)
        evaluation = getattr(engine, "eval", None)

        ui_error_message = (
            "MATLAB launcher UI is not available. Launch MATLAB, run 'slap2_launcher', "
            "and ensure the shared UI is open before starting the Python launcher."
        )

        if callable(feval_func):
            try:
                helper_info = feval_func(
                    "slap2_launcher", "helper_register", nargout=1
                )
            except Exception as exc:
                raise RuntimeError(ui_error_message) from exc

            try:
                feval_func("slap2_launcher", "helper_set_python_start_time", nargout=0)
            except Exception:
                pass

            _call_status_updater()
            return helper_info

        if callable(evaluation):
            try:
                helper_info = evaluation(
                    "slap2_launcher('helper_register')", nargout=1
                )
            except Exception as exc:
                raise RuntimeError(ui_error_message) from exc

            try:
                evaluation(
                    "slap2_launcher('helper_set_python_start_time')", nargout=0
                )
            except Exception:
                pass

            _call_status_updater()

        return helper_info

        raise RuntimeError(ui_error_message)

    def _log_helper_metadata(self, helper_info: Optional[Any]) -> None:
        if helper_info is None:
            return

        def _normalise_matlab_value(value: Any) -> Optional[Any]:
            if value is None:
                return None
            if isinstance(value, (list, tuple)) and len(value) == 1:
                return _normalise_matlab_value(value[0])
            tolist = getattr(value, "tolist", None)
            if callable(tolist):
                try:
                    items = tolist()
                except Exception:
                    items = None
                if isinstance(items, list) and items:
                    if len(items) == 1:
                        return _normalise_matlab_value(items[0])
                    return items
            if isinstance(value, bytes):
                try:
                    return value.decode("utf-8", errors="ignore")
                except Exception:
                    return value.decode(errors="ignore")
            return value

        def _extract_field(info: Any, *field_names: str) -> Optional[Any]:
            for field in field_names:
                for accessor in (
                    lambda obj=info, key=field: obj[key],
                    lambda obj=info, key=field: obj[0][key],
                    lambda obj=info, key=field: getattr(obj, key, None),
                ):
                    try:
                        value = accessor()
                    except Exception:
                        continue
                    value = _normalise_matlab_value(value)
                    if value is not None:
                        return value
            return None

        def _log_helper_detail(label: str, value: Optional[Any]) -> None:
            if value is None:
                return
            text = value if isinstance(value, str) else str(value)
            if not text:
                return
            detail_message = f"MATLAB {label}: {text}"
            logging.info(detail_message)
            self._stdout_queue.put(detail_message)

        launcher_version = _extract_field(helper_info, "launcher_version", "version")
        rig_source = _extract_field(
            helper_info,
            "rig_description_source",
            "rig_description_path",
        )
        rig_target = _extract_field(helper_info, "rig_description_target")
        timestamp = _extract_field(helper_info, "timestamp")

        if launcher_version is None:
            logging.debug("Unexpected MATLAB helper metadata: %r", helper_info)

        _log_helper_detail("launcher version", launcher_version)
        _log_helper_detail("rig description source", rig_source)
        _log_helper_detail("rig description copy", rig_target)

        if timestamp is not None:
            _log_helper_detail("helper timestamp", timestamp)

    def _monitor_future(self) -> None:  # pragma: no cover - relies on MATLAB runtime
        matlab_engine = _ensure_matlab_engine()
        matlab_execution_error = getattr(matlab_engine, "MatlabExecutionError", Exception)
        cancelled_error = getattr(matlab_engine, "CancelledError", Exception)

        fatal_error_types = tuple(
            err
            for err in (
                getattr(matlab_engine, "EngineError", None),
                getattr(matlab_engine, "ConnectionError", None),
            )
            if err is not None
        )

        while True:
            future = self._future
            if future is None:
                self.returncode = 1
                self._stderr_queue.put(
                    "MATLAB future handle unavailable; aborting acquisition"
                )
                break

            try:
                future.result()
                if self.returncode is None:
                    self.returncode = 0
                break
            except cancelled_error:
                self.returncode = -1
                break
            except matlab_execution_error as exc:  # pragma: no cover - MATLAB specific
                self.returncode = 1
                self._stderr_queue.put(str(exc))
                break
            except Exception as exc:  # pragma: no cover - defensive
                if self._terminated:
                    self.returncode = -1 if self.returncode is None else self.returncode
                    break

                resumable = False
                if self._request.enable_resume:
                    if fatal_error_types and isinstance(exc, fatal_error_types):
                        resumable = True
                    else:
                        message = str(exc).lower()
                        resume_tokens = (
                            "engine has terminated",
                            "connection lost",
                            "engine closed",
                            "invalid matlab engine",
                        )
                        resumable = any(token in message for token in resume_tokens)

                if resumable and self._attempt_resume(exc):
                    continue

                self.returncode = 1
                self._stderr_queue.put(str(exc))
                break

        self._finalize_streams()
        self._done.set()

    def poll(self) -> Optional[int]:
        return self.returncode if self._done.is_set() else None

    def wait(self, timeout: Optional[float] = None) -> Optional[int]:
        if timeout is None:
            self._done.wait()
        else:
            if not self._done.wait(timeout):
                raise subprocess.TimeoutExpired(self._request.entry_point, timeout)
        return self.returncode

    def terminate(self) -> None:
        if self._done.is_set():
            return

        self._terminated = True
        future = self._future
        try:
            if future is not None:
                future.cancel()  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - defensive
            logging.debug("MATLAB engine cancel request failed: %s", exc)

        self._done.wait(self._request.cancel_timeout_sec)
        if not self._done.is_set():
            logging.warning(
                "MATLAB entry point '%s' did not respond to cancellation within %.1fs",
                self._request.entry_point,
                self._request.cancel_timeout_sec,
            )
            self._finalize_streams()

    def kill(self) -> None:
        self.terminate()

    def close_streams(self) -> None:
        self._finalize_streams()

    def _wait_for_engine_recovery(self) -> Optional[Any]:
        """Keep attempting to reconnect to the shared engine until available."""

        poll_interval = max(0.1, float(self._request.connect_poll_sec or 1.0))
        attempt = 0

        while not self._terminated:
            attempt += 1
            try:
                return self._engine_connector()
            except Exception as exc:  # pragma: no cover - depends on MATLAB runtime
                message = (
                    "MATLAB engine '%s' unavailable while recovering from a crash (%s). "
                    "Waiting for MATLAB to restart so the Python launcher can reconnect..."
                )
                logging.error(message, self._request.engine_name, exc)
                self._stderr_queue.put(
                    f"MATLAB engine '{self._request.engine_name}' unavailable during resume: {exc}"
                )
                if self._terminated:
                    break
                time.sleep(poll_interval)

        return None

    def _finalize_streams(self) -> None:
        if self._streams_closed:
            return
        self._streams_closed = True
        try:
            self._stdout_sink.close()
        except Exception:  # pragma: no cover - defensive
            pass
        try:
            self._stderr_sink.close()
        except Exception:  # pragma: no cover - defensive
            pass
        # Signal readers to stop
        self._stdout_queue.put(None)
        self._stderr_queue.put(None)

    def _attempt_resume(self, exc: Exception) -> bool:
        logging.error(
            "MATLAB engine failure detected on attempt %d: %s",
            self._attempt,
            exc,
        )
        self._stderr_queue.put(f"MATLAB engine failure detected: {exc}")

        if self._terminated:
            logging.info("Resume skipped because termination was requested.")
            return False

        logging.info(
            "Waiting for MATLAB engine '%s' to become available for resume attempt %d",
            self._request.engine_name,
            self._attempt + 1,
        )

        new_engine = self._wait_for_engine_recovery()

        if new_engine is None:
            if self._terminated:
                logging.info("Resume aborted after reconnection attempts due to termination request.")
            else:
                logging.error(
                    "Could not reconnect to MATLAB engine '%s'; giving up on resume",
                    self._request.engine_name,
                )
            return False

        if self._terminated:
            logging.info("Resume aborted after reconnection due to termination request.")
            try:
                disconnect = getattr(new_engine, "disconnect", None)
                if callable(disconnect):
                    disconnect()
            except Exception:
                pass
            return False

        try:
            self._start_call(new_engine)
            logging.info(
                "Resume attempt %d dispatched on MATLAB engine '%s'",
                self._attempt,
                self._request.engine_name,
            )
            self._stderr_queue.put(
                f"MATLAB resume attempt {self._attempt} dispatched after reconnection"
            )
            return True
        except Exception as start_exc:
            logging.error("Failed to restart MATLAB entry point: %s", start_exc)
            try:
                disconnect = getattr(new_engine, "disconnect", None)
                if callable(disconnect):
                    disconnect()
            except Exception:
                pass
            self._stderr_queue.put(f"Failed to restart MATLAB entry point: {start_exc}")
            return False


def start_matlab_function(
    engine: Any,
    request: MatlabLaunchRequest,
    engine_connector: Optional[Callable[[], Any]] = None,
) -> MatlabEngineProcess:
    """Invoke the requested MATLAB function using the shared engine."""

    stdout_queue: "queue.Queue[Optional[str]]" = queue.Queue()
    stderr_queue: "queue.Queue[Optional[str]]" = queue.Queue()
    stdout_sink = _MatlabStreamSink(stdout_queue)
    stderr_sink = _MatlabStreamSink(stderr_queue)

    if engine_connector is None:
        engine_connector = lambda: connect_shared_engine(request)

    process = MatlabEngineProcess(
        engine=engine,
        stdout_queue=stdout_queue,
        stderr_queue=stderr_queue,
        stdout_sink=stdout_sink,
        stderr_sink=stderr_sink,
        request=request,
        engine_connector=engine_connector,
    )

    logging.info(
        "Dispatched MATLAB entry point '%s' (engine '%s')",
        request.entry_point,
        request.engine_name,
    )
    return process


def _dispatch_matlab_feval(
    engine: Any,
    entry_point: str,
    call_args: List[Any],
    nargout: int,
    stdout_sink: _MatlabStreamSink,
    stderr_sink: _MatlabStreamSink,
):
    """Invoke engine.feval using the preferred async keyword for the runtime.

    MATLAB replaced the legacy ``async`` keyword argument with ``background``.
    Try the new spelling first, then fall back to ``async`` for older engines.
    """

    base_kwargs = {
        "nargout": nargout,
        "stdout": stdout_sink,
        "stderr": stderr_sink,
    }

    # Prefer ``background=True`` (MATLAB R2024b+), then fall back to ``async=True``
    # for older engine builds that do not recognise ``background`` yet.
    for keyword in ("background", "async"):
        call_kwargs = dict(base_kwargs)
        call_kwargs[keyword] = True
        try:
            return engine.feval(entry_point, *call_args, **call_kwargs)
        except TypeError as exc:
            message = str(exc).lower()
            if keyword == "background" and "background" in message:
                continue
            raise
        except Exception as exc:  # pragma: no cover - defensive fallback
            message = str(exc).lower()
            if keyword == "background" and "background" in message:
                continue
            raise

    raise RuntimeError(
        "MATLAB engine did not accept either 'background' or 'async' keyword for async execution"
    )


def cleanup_engine(
    engine: Optional[Any],
    process: Optional[MatlabEngineProcess],
    keep_engine_alive: bool = True,
) -> None:
    """Release engine resources after the launcher completes."""

    if process is not None:
        process.close_streams()

    if engine is None:
        return

    try:  # pragma: no cover - relies on MATLAB runtime
        if keep_engine_alive:
            release = _resolve_engine_method(engine, ("close", "disconnect"))
            if release is not None:
                release()
        else:
            quit_fn = getattr(engine, "quit", None)
            if callable(quit_fn):
                quit_fn()
            else:
                release = _resolve_engine_method(engine, ("close", "disconnect"))
                if release is not None:
                    release()
    except Exception as exc:
        logging.debug("Error while releasing MATLAB engine: %s", exc)


def _resolve_engine_method(engine: Any, candidates: List[str]) -> Optional[Callable[[], Any]]:
    """Return the first callable method found on the engine from ``candidates``."""

    for name in candidates:
        method = getattr(engine, name, None)
        if callable(method):
            return method
    return None
