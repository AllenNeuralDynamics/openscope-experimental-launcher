"""Helpers for reading and writing routing manifest files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def read_manifest_entries(manifest_path: Path) -> List[Dict[str, Any]]:
    """Return manifest entries list; empty on missing/invalid."""
    if not manifest_path.exists():
        return []
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return data.get("entries", []) if isinstance(data, dict) else []
    except Exception:
        return []


def write_manifest(manifest_path: Path, entries: List[Dict[str, Any]]) -> None:
    """Write entries to manifest path, creating parent dirs."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"entries": entries}, indent=2), encoding="utf-8")
