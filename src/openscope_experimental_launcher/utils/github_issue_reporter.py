"""GitHub issue reporting utilities.

This module provides an opt-in crash reporting path that can create a GitHub Issue
when the launcher encounters an unexpected exception.

Design goals:
- Never raise from reporting (must not crash the launcher)
- Avoid leaking secrets; include only minimal, non-sensitive context by default
- Be configurable via param file / rig config + environment variables
"""

from __future__ import annotations

import json
import logging
import os
import platform
import re
import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests


@dataclass(frozen=True)
class GitHubIssueConfig:
    enabled: bool
    repo: str
    api_base_url: str
    token_env: str
    labels: Tuple[str, ...]
    report_on: Tuple[str, ...]
    include_subject_user: bool
    include_rig_config: bool
    include_launcher_log: bool
    launcher_log_mode: str
    sanitize_launcher_log: bool
    max_output_lines: int
    max_body_chars: int


def _as_tuple(value: Any) -> Tuple[str, ...]:
    if not value:
        return tuple()
    if isinstance(value, (list, tuple)):
        return tuple(str(v) for v in value if v is not None)
    return (str(value),)


def load_github_issue_config(params: Dict[str, Any]) -> Optional[GitHubIssueConfig]:
    """Load crash issue reporting config from merged launcher params.

    Supports either:
    - `github_issue: { ... }` (preferred)
    - legacy/flat keys (best-effort): github_issue_on_error, github_issue_repo, ...
    """

    cfg = params.get("github_issue")
    if cfg is None:
        # Flat/legacy keys
        enabled = bool(params.get("github_issue_on_error", False))
        repo = params.get("github_issue_repo")
        if not (enabled and repo):
            return None
        cfg = {
            "enabled": enabled,
            "repo": repo,
            "api_base_url": params.get("github_issue_api_base_url"),
            "token_env": params.get("github_issue_token_env"),
            "labels": params.get("github_issue_labels"),
            "report_on": params.get("github_issue_report_on"),
            "include_subject_user": params.get("github_issue_include_subject_user"),
            "include_rig_config": params.get("github_issue_include_rig_config"),
            "include_launcher_log": params.get("github_issue_include_launcher_log"),
            "launcher_log_mode": params.get("github_issue_launcher_log_mode"),
            "sanitize_launcher_log": params.get("github_issue_sanitize_launcher_log"),
            "max_output_lines": params.get("github_issue_max_output_lines"),
            "max_body_chars": params.get("github_issue_max_body_chars"),
        }

    try:
        enabled = bool(cfg.get("enabled", False))
        repo = str(cfg.get("repo") or "").strip()
        if not (enabled and repo):
            return None

        api_base_url = str(cfg.get("api_base_url") or "https://api.github.com").rstrip("/")
        token_env = str(cfg.get("token_env") or "GITHUB_ISSUE_TOKEN")
        labels = _as_tuple(cfg.get("labels") or ("auto-report",))

        # When reporting is enabled, default to reporting the most actionable failures.
        report_on = _as_tuple(cfg.get("report_on") or ("exception", "pre_acquisition", "post_acquisition"))

        include_subject_user = bool(cfg.get("include_subject_user", False))
        include_rig_config = bool(cfg.get("include_rig_config", False))

        # Include launcher.log by default.
        include_launcher_log = bool(cfg.get("include_launcher_log", True))
        launcher_log_mode = str(cfg.get("launcher_log_mode") or "full").strip().lower()
        if launcher_log_mode not in {"full", "tail"}:
            launcher_log_mode = "full"

        # No sanitization by default (user requested full fidelity).
        sanitize_launcher_log = bool(cfg.get("sanitize_launcher_log", False))

        max_output_lines = int(cfg.get("max_output_lines", 80))
        max_body_chars = int(cfg.get("max_body_chars", 60000))

        return GitHubIssueConfig(
            enabled=enabled,
            repo=repo,
            api_base_url=api_base_url,
            token_env=token_env,
            labels=labels,
            report_on=report_on,
            include_subject_user=include_subject_user,
            include_rig_config=include_rig_config,
            include_launcher_log=include_launcher_log,
            launcher_log_mode=launcher_log_mode,
            sanitize_launcher_log=sanitize_launcher_log,
            max_output_lines=max_output_lines,
            max_body_chars=max_body_chars,
        )
    except Exception as exc:  # pragma: no cover
        logging.warning("Invalid github_issue configuration: %s", exc)
        return None


def _tail_lines(lines: Iterable[str], max_lines: int) -> List[str]:
    if max_lines <= 0:
        return []
    items = [str(x) for x in lines if x is not None]
    if len(items) <= max_lines:
        return items
    return items[-max_lines:]


_RE_SUBJECT_ID = re.compile(r"(Subject ID:\s*)([^,\n\r]+)")
_RE_USER_ID = re.compile(r"(User ID:\s*)([^,\n\r]+)")
_RE_JSON_SUBJECT_ID = re.compile(r"(\"subject_id\"\s*:\s*)(\"[^\"]*\"|\d+)")
_RE_JSON_USER_ID = re.compile(r"(\"user_id\"\s*:\s*)(\"[^\"]*\"|\d+)")


def _sanitize_log_tail(lines: List[str], *, include_subject_user: bool) -> List[str]:
    if include_subject_user:
        return lines
    sanitized: List[str] = []
    for line in lines:
        line = _RE_SUBJECT_ID.sub(r"\1<redacted>", line)
        line = _RE_USER_ID.sub(r"\1<redacted>", line)
        line = _RE_JSON_SUBJECT_ID.sub(r"\1\"<redacted>\"", line)
        line = _RE_JSON_USER_ID.sub(r"\1\"<redacted>\"", line)
        sanitized.append(line)
    return sanitized


def _read_text_tail(path: str, *, max_lines: int) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return _tail_lines(f.readlines(), max_lines)
    except Exception:
        return []


def _read_text_full(path: str) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.readlines()
    except Exception:
        return []


def _read_launcher_log_lines(*, cfg: GitHubIssueConfig, log_path: str) -> List[str]:
    if not cfg.include_launcher_log:
        return []
    if not os.path.exists(log_path):
        return []
    if cfg.launcher_log_mode == "tail":
        lines = _read_text_tail(log_path, max_lines=cfg.max_output_lines)
    else:
        lines = _read_text_full(log_path)

    if cfg.sanitize_launcher_log and not cfg.include_subject_user:
        lines = _sanitize_log_tail(lines, include_subject_user=False)
    return lines


def _should_report(cfg: GitHubIssueConfig, kind: str) -> bool:
    kind_norm = (kind or "").strip().lower()
    enabled_kinds = {k.strip().lower() for k in (cfg.report_on or tuple()) if k}
    return kind_norm in enabled_kinds


def _read_json_file(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _update_debug_state_with_issue(debug_state_path: str, issue_url: str, issue_number: Optional[int]) -> None:
    try:
        payload = _read_json_file(debug_state_path) or {}
        payload.setdefault("github", {})
        payload["github"]["issue_url"] = issue_url
        if issue_number is not None:
            payload["github"]["issue_number"] = issue_number
        payload["github"]["reported_at"] = datetime.now().isoformat()
        with open(debug_state_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception as exc:
        logging.debug("Failed to update debug_state with issue url: %s", exc)


def _build_issue_title(launcher_type: str, exc: Exception, session_uuid: str, version: str) -> str:
    exc_name = exc.__class__.__name__
    uuid_part = session_uuid or "unknown-session"
    ver_part = version or "unknown-version"
    return f"Crash: {exc_name} in {launcher_type} ({ver_part}) [{uuid_part}]"


def _build_issue_body(
    *,
    cfg: GitHubIssueConfig,
    launcher_type: str,
    version: str,
    rig_id: Optional[str],
    session_uuid: str,
    param_file: Optional[str],
    exc: Optional[Exception],
    traceback_text: Optional[str],
    stderr_tail: List[str],
    stdout_tail: List[str],
    launcher_log_tail: List[str],
    debug_state_path: Optional[str],
    params: Dict[str, Any],
) -> str:
    # Keep this conservative: no secrets, no subject/user unless explicitly enabled.
    lines: List[str] = []
    lines.append("This issue was created automatically by the launcher after an unexpected exception.")
    lines.append("")
    lines.append("### Context")
    lines.append(f"- Launcher type: `{launcher_type}`")
    lines.append(f"- Launcher version: `{version}`")
    if rig_id:
        lines.append(f"- Rig ID: `{rig_id}`")
    lines.append(f"- Session UUID: `{session_uuid or 'unknown'}`")
    lines.append(f"- OS: `{platform.platform()}`")
    lines.append(f"- Python: `{platform.python_version()}`")
    if param_file:
        lines.append(f"- Param file: `{param_file}`")
    if debug_state_path:
        lines.append(f"- Debug state: `{debug_state_path}`")

    if cfg.include_subject_user:
        subject_id = params.get("subject_id")
        user_id = params.get("user_id")
        if subject_id:
            lines.append(f"- subject_id: `{subject_id}`")
        if user_id:
            lines.append(f"- user_id: `{user_id}`")

    if cfg.include_rig_config:
        try:
            rig_cfg = params.get("rig_config")
            if rig_cfg is not None:
                lines.append("")
                lines.append("### Rig Config (as merged)")
                lines.append("```json")
                lines.append(json.dumps(rig_cfg, indent=2)[: cfg.max_body_chars])
                lines.append("```")
        except Exception:
            pass

    lines.append("")
    lines.append("### Exception")
    lines.append("```text")
    if exc is None:
        lines.append("(no exception)")
    else:
        lines.append(f"{exc.__class__.__name__}: {exc}")
    lines.append("```")

    if stderr_tail:
        lines.append("")
        lines.append("### Recent stderr")
        lines.append("```text")
        lines.extend(stderr_tail)
        lines.append("```")

    if stdout_tail:
        lines.append("")
        lines.append("### Recent stdout")
        lines.append("```text")
        lines.extend(stdout_tail)
        lines.append("```")

    if launcher_log_tail:
        lines.append("")
        lines.append("### launcher.log (tail)")
        lines.append("```text")
        lines.extend(launcher_log_tail)
        lines.append("```")

    if traceback_text:
        lines.append("")
        lines.append("### Traceback")
        lines.append("```text")
        lines.append(traceback_text)
        lines.append("```")

    body = "\n".join(lines)
    if len(body) > cfg.max_body_chars:
        body = body[: cfg.max_body_chars - 50] + "\n\n...(truncated)"
    return body


def create_issue(*, cfg: GitHubIssueConfig, title: str, body: str) -> Optional[Tuple[str, Optional[int]]]:
    """Create an issue in the configured repo. Returns (url, number) on success."""

    token = os.environ.get(cfg.token_env)
    if not token:
        logging.warning(
            "GitHub issue reporting enabled but token env var '%s' is not set; skipping.",
            cfg.token_env,
        )
        return None

    url = f"{cfg.api_base_url}/repos/{cfg.repo}/issues"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {token}",
    }
    payload: Dict[str, Any] = {
        "title": title,
        "body": body,
    }
    if cfg.labels:
        payload["labels"] = list(cfg.labels)

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code not in (200, 201):
            logging.warning(
                "Failed to create GitHub issue (%s): %s", resp.status_code, resp.text
            )
            return None
        data = resp.json() if resp.content else {}
        issue_url = data.get("html_url") or data.get("url") or ""
        issue_number = data.get("number")
        if issue_url:
            logging.info("Created GitHub issue: %s", issue_url)
            return (issue_url, int(issue_number) if issue_number is not None else None)
        logging.info("Created GitHub issue (no url in response)")
        return ("", int(issue_number) if issue_number is not None else None)
    except Exception as exc:
        logging.warning("GitHub issue reporting failed: %s", exc)
        return None


def report_exception(
    *,
    params: Dict[str, Any],
    launcher_type: str,
    version: str,
    rig_id: Optional[str],
    session_uuid: str,
    param_file: Optional[str],
    exc: Exception,
    stderr_lines: Iterable[str] = (),
    stdout_lines: Iterable[str] = (),
    output_directory: Optional[str] = None,
) -> Optional[str]:
    """Create a GitHub issue for an exception if enabled.

    Returns the created issue URL (if any).
    """

    cfg = load_github_issue_config(params)
    if not cfg:
        return None
    if not _should_report(cfg, "exception"):
        return None

    traceback_text = traceback.format_exc() or "(no traceback available)"
    stderr_tail = _tail_lines(stderr_lines, cfg.max_output_lines)
    stdout_tail = _tail_lines(stdout_lines, cfg.max_output_lines)

    launcher_log_tail: List[str] = []
    if output_directory:
        log_path = os.path.join(output_directory, "launcher_metadata", "launcher.log")
        launcher_log_tail = _read_launcher_log_lines(cfg=cfg, log_path=log_path)

    debug_state_path = None
    if output_directory:
        candidate = os.path.join(output_directory, "launcher_metadata", "debug_state.json")
        if os.path.exists(candidate):
            debug_state_path = candidate

    title = _build_issue_title(launcher_type, exc, session_uuid, version)
    body = _build_issue_body(
        cfg=cfg,
        launcher_type=launcher_type,
        version=version,
        rig_id=rig_id,
        session_uuid=session_uuid,
        param_file=param_file,
        exc=exc,
        traceback_text=traceback_text,
        stderr_tail=stderr_tail,
        stdout_tail=stdout_tail,
        launcher_log_tail=launcher_log_tail,
        debug_state_path=debug_state_path,
        params=params,
    )

    created = create_issue(cfg=cfg, title=title, body=body)
    if not created:
        return None

    issue_url, issue_number = created
    if debug_state_path and issue_url:
        _update_debug_state_with_issue(debug_state_path, issue_url, issue_number)

    return issue_url


def report_stage_failure(
    *,
    params: Dict[str, Any],
    launcher_type: str,
    version: str,
    rig_id: Optional[str],
    session_uuid: str,
    param_file: Optional[str],
    stage_kind: str,
    stage_name: str,
    failed_steps: List[str],
    output_directory: Optional[str] = None,
) -> Optional[str]:
    """Create a GitHub issue when a stage reports failure (pre/post acquisition)."""

    cfg = load_github_issue_config(params)
    if not cfg:
        return None
    if not _should_report(cfg, stage_kind):
        return None

    short_failed = [s for s in (failed_steps or []) if s]
    title = f"Failure: {stage_name} pipeline in {launcher_type} ({version}) [{session_uuid or 'unknown-session'}]"

    launcher_log_tail: List[str] = []
    if output_directory:
        log_path = os.path.join(output_directory, "launcher_metadata", "launcher.log")
        launcher_log_tail = _read_launcher_log_lines(cfg=cfg, log_path=log_path)

    # Build a body that looks similar to crash reports, but without traceback.
    lines: List[str] = []
    lines.append("This issue was created automatically by the launcher after a pipeline stage reported failure.")
    lines.append("")
    lines.append("### Context")
    lines.append(f"- Stage: `{stage_name}`")
    lines.append(f"- Launcher type: `{launcher_type}`")
    lines.append(f"- Launcher version: `{version}`")
    if rig_id:
        lines.append(f"- Rig ID: `{rig_id}`")
    lines.append(f"- Session UUID: `{session_uuid or 'unknown'}`")
    lines.append(f"- OS: `{platform.platform()}`")
    lines.append(f"- Python: `{platform.python_version()}`")
    if param_file:
        lines.append(f"- Param file: `{param_file}`")
    if short_failed:
        lines.append("")
        lines.append("### Failed steps")
        lines.append("```text")
        lines.extend(short_failed)
        lines.append("```")
    if launcher_log_tail:
        lines.append("")
        lines.append("### launcher.log (tail)")
        lines.append("```text")
        lines.extend(launcher_log_tail)
        lines.append("```")

    body = "\n".join(lines)
    if len(body) > cfg.max_body_chars:
        body = body[: cfg.max_body_chars - 50] + "\n\n...(truncated)"

    created = create_issue(cfg=cfg, title=title, body=body)
    if not created:
        return None
    issue_url, _issue_number = created
    return issue_url
