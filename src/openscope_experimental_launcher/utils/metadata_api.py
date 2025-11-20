"""Utilities for interacting with the AIND metadata service."""
from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

try:  # pragma: no cover - optional dependency fallback handled at runtime
    import requests  # type: ignore[import-not-found]
except ModuleNotFoundError as exc:  # pragma: no cover - environment without requests
    requests = None  # type: ignore[assignment]
    _REQUESTS_IMPORT_ERROR = exc
else:  # pragma: no cover - import success path simple
    _REQUESTS_IMPORT_ERROR = None
from urllib.parse import urljoin

DEFAULT_TIMEOUT = 10.0
DEFAULT_BASE_URL = "http://aind-metadata-service"


class MetadataServiceError(RuntimeError):
    """Raised when the metadata service returns an error."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        url: Optional[str] = None,
        body: Optional[str] = None,
        payload: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.url = url
        self.body = body
        self.payload = payload


def _normalize_base_url(base_url: str) -> str:
    if not base_url:
        raise MetadataServiceError("metadata_service_base_url parameter is required")
    return base_url.rstrip("/") + "/"


def build_url(base_url: str, relative_path: str) -> str:
    """Construct an absolute URL from a base and relative path."""
    normalized = _normalize_base_url(base_url)
    return urljoin(normalized, relative_path.lstrip("/"))


def fetch_json(
    base_url: str,
    relative_path: str,
    *,
    params: Optional[Mapping[str, Any]] = None,
    headers: Optional[Mapping[str, str]] = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> Any:
    """Fetch JSON from the metadata service."""
    if requests is None:
        raise MetadataServiceError(
            "The 'requests' package is required for metadata service calls; install it via project dependencies."
        ) from _REQUESTS_IMPORT_ERROR
    url = build_url(base_url, relative_path)
    logging.debug("Requesting metadata service endpoint %s", url)
    try:
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
    except requests.RequestException as exc:  # pragma: no cover - network failures handled uniformly
        raise MetadataServiceError(f"Request to metadata service failed: {exc}") from exc

    payload: Any = None
    try:
        payload = response.json()
    except ValueError:
        payload = None

    if response.status_code != 200:
        body_preview = response.text[:500] if response.text else "<no body>"
        raise MetadataServiceError(
            f"Metadata service responded with {response.status_code} for {url}: {body_preview}",
            status_code=response.status_code,
            url=url,
            body=response.text,
            payload=payload,
        )

    if payload is None:
        raise MetadataServiceError(
            f"Metadata service returned non-JSON payload for {url}",
            status_code=response.status_code,
            url=url,
            body=response.text,
        )

    return payload


def resolve_base_url(params: Mapping[str, Any]) -> str:
    """Find the metadata service base URL from launcher parameters."""
    for key in ("metadata_service_base_url", "metadata_api_base_url"):
        if params.get(key):
            return str(params[key])
    logging.debug(
        "No metadata base URL provided; using default '%s'",
        DEFAULT_BASE_URL,
    )
    return DEFAULT_BASE_URL


def resolve_timeout(params: Mapping[str, Any]) -> float:
    """Return timeout setting for metadata requests."""
    value = params.get("metadata_service_timeout")
    try:
        return float(value) if value is not None else DEFAULT_TIMEOUT
    except (TypeError, ValueError):
        logging.warning("Invalid metadata_service_timeout '%s'; falling back to default", value)
        return DEFAULT_TIMEOUT
