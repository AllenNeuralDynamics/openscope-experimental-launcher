"""Lightweight JSON Schema validation for launcher parameter files.

This intentionally avoids external dependencies so it can run on rigs without
extra packages. It mirrors the validation used in `openscope-params/tooling`
but is packaged with the launcher for runtime checks.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlparse
from urllib.request import urlopen


# Default remote locations for schemas when not found locally. These mirror
# the public `openscope-params` repository layout.
LAUNCHER_SCHEMA_URL = (
    "https://raw.githubusercontent.com/AllenNeuralDynamics/openscope-params/main/tooling/model_launcher.schema.json"
)
MODULE_SCHEMA_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/AllenNeuralDynamics/openscope-params/main/tooling/model_{name}.schema.json"
)


def _is_url(value: str) -> bool:
    try:
        u = urlparse(value)
    except Exception:
        return False
    return u.scheme in {"http", "https"}


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _discover_schema_roots(param_path: Path) -> list[Path]:
    """Locate a nearby tooling directory containing schemas.

    Walks ancestors looking for tooling/model_launcher.schema.json so rigs with
    a local clone of openscope-params work offline.
    """

    roots: list[Path] = []
    for ancestor in param_path.resolve().parents:
        candidate = ancestor / "tooling" / "model_launcher.schema.json"
        if candidate.exists():
            roots.append(candidate.parent)
            break
    return roots


def _resolve_schema(
    *,
    param_path: Path,
    schema_ref: str,
    roots: Iterable[Path],
    allow_launcher_local: bool = False,
) -> Dict[str, Any]:
    """Resolve a schema reference to JSON.

    Resolution order:
    1. Local paths relative to param file
    2. Local roots/tooling (if provided)
    3. Repo-root candidates (roots given)
    4. HTTP(S) fetch
    """

    if not schema_ref:
        raise RuntimeError("Empty schema reference provided")

    # Local path (relative)
    if not _is_url(schema_ref) and not schema_ref.startswith("file://"):
        ref = schema_ref.strip()
        if ref.startswith("./"):
            ref = ref[2:]

        # Build candidate paths
        candidates: list[Path] = []
        candidates.append((param_path.parent / ref).resolve())
        for root in roots:
            root_path = Path(root).resolve()
            if ref.startswith("tooling/"):
                candidates.append((root_path / ref).resolve())
            candidates.append((root_path / ref).resolve())

        for candidate in candidates:
            if candidate.exists():
                return _load_json(candidate)

        raise FileNotFoundError(f"Schema file not found (searched {candidates[0]})")

    # Remote URL
    parsed = urlparse(schema_ref)
    if parsed.scheme in {"http", "https"}:
        # Allow using local launcher schema if explicitly requested to avoid a fetch
        if (
            allow_launcher_local
            and parsed.netloc == "raw.githubusercontent.com"
            and parsed.path.endswith("/tooling/model_launcher.schema.json")
        ):
            for root in roots:
                candidate = Path(root) / "model_launcher.schema.json"
                if candidate.exists():
                    return _load_json(candidate)
        with urlopen(schema_ref) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Unable to fetch schema URL {schema_ref!r}: HTTP {resp.status}")
            data = resp.read().decode("utf-8")
            return json.loads(data)

    raise RuntimeError(
        f"Schema refs of this form are not supported: {schema_ref!r}. Use a local path or HTTP(S) URL."
    )


def _validate_object_against_schema(payload: Dict[str, Any], schema: Dict[str, Any]) -> None:
    required = schema.get("required", [])
    for key in required:
        if key not in payload or payload.get(key) is None:
            raise RuntimeError(f"Missing required key {key!r}")

    properties = schema.get("properties", {})
    for key, rules in properties.items():
        if key not in payload:
            continue
        expected = rules.get("type")
        if not expected:
            continue

        value = payload.get(key)
        if value is None:
            continue

        expected_types = expected if isinstance(expected, list) else [expected]
        type_ok = False
        for t in expected_types:
            if t == "string" and isinstance(value, str):
                type_ok = True
            elif t == "integer" and isinstance(value, int) and not isinstance(value, bool):
                type_ok = True
            elif t == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
                type_ok = True
            elif t == "object" and isinstance(value, dict):
                type_ok = True
            elif t == "array" and isinstance(value, list):
                type_ok = True
            elif t == "boolean" and isinstance(value, bool):
                type_ok = True
            elif t == "null" and value is None:
                type_ok = True
        if not type_ok:
            raise RuntimeError(f"Key {key!r} expected type {expected!r}, got {type(value).__name__}")


def _load_module_schemas(roots: Iterable[Path]) -> dict[str, Dict[str, Any]]:
    schemas: dict[str, Dict[str, Any]] = {}
    for root in roots:
        tooling_dir = Path(root)
        if not tooling_dir.exists():
            continue
        for path in sorted(tooling_dir.glob("model_*.schema.json")):
            if path.name == "model_launcher.schema.json":
                continue
            data = _load_json(path)
            name = path.stem.removeprefix("model_")
            schemas[name] = data
    return schemas


def validate_param_file(param_path: Path, payload: Optional[Dict[str, Any]] = None) -> None:
    """Validate a launcher parameter file against JSON Schemas.

    - Validates the top-level launcher schema using $schema (or the default URL).
    - Validates launcher_module entries against module schemas when available.
    """

    param_path = Path(param_path).resolve()
    payload = payload if payload is not None else _load_json(param_path)

    # Discover local schema roots (tooling/) near the param file for offline use.
    discovered_roots = _discover_schema_roots(param_path)

    schema_ref = payload.get("$schema") or LAUNCHER_SCHEMA_URL
    launcher_schema = _resolve_schema(
        param_path=param_path,
        schema_ref=str(schema_ref),
        roots=discovered_roots,
        allow_launcher_local=True,
    )
    _validate_object_against_schema(payload, launcher_schema)

    module_schemas = _load_module_schemas(discovered_roots)

    def _validate_pipeline(pipeline):
        if not isinstance(pipeline, list):
            return
        for entry in pipeline:
            if not isinstance(entry, dict):
                continue
            module_path = entry.get("module_path")
            module_type = entry.get("module_type")
            if module_type and module_type != "launcher_module":
                continue
            params = entry.get("module_parameters")
            if not isinstance(params, dict):
                continue

            schema_override = entry.get("module_schema")
            module_schema = None
            if schema_override:
                module_schema = _resolve_schema(
                    param_path=param_path,
                    schema_ref=str(schema_override),
                    roots=discovered_roots,
                )
            elif module_path:
                module_schema = module_schemas.get(module_path)
                if module_schema is None and module_path:
                    # Best-effort remote fetch if not packaged locally
                    try:
                        remote_url = MODULE_SCHEMA_URL_TEMPLATE.format(name=module_path)
                        module_schema = _resolve_schema(
                            param_path=param_path,
                            schema_ref=remote_url,
                            roots=(),
                        )
                    except Exception:
                        module_schema = None

            if module_schema:
                _validate_object_against_schema(params, module_schema)

    _validate_pipeline(payload.get("pre_acquisition_pipeline"))
    _validate_pipeline(payload.get("post_acquisition_pipeline"))
