from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from openscope_experimental_launcher.utils import manifest_utils, param_utils

LOG = logging.getLogger(__name__)


_DEF_ROOT = "behavior-videos"
_DEF_EXTS = {".avi", ".mp4", ".mpeg", ".mpg", ".mov", ".mkv", ".mjpg", ".mjpeg", ".h264"}


def _load_params(param_source: Any, overrides: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if isinstance(param_source, Mapping):
        params = dict(param_source)
        if overrides:
            params.update(overrides)
        return params
    return param_utils.load_parameters(param_file=param_source, overrides=overrides)


def _find_behavior_roots(session_dir: Path, root_name: str) -> List[Path]:
    roots: List[Path] = []
    for path in session_dir.rglob(root_name):
        if path.is_dir():
            roots.append(path)
    return roots


def _iter_nested_files(root: Path, exts: Iterable[str]) -> List[Path]:
    targets = []
    ext_set = {e.lower() for e in exts}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in ext_set:
            continue
        targets.append(path)
    return targets


def _next_available(dest: Path) -> Path:
    if not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}_dup{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _remove_empty_dirs(root: Path) -> None:
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_dir():
            try:
                next(path.iterdir())
            except StopIteration:
                try:
                    path.rmdir()
                except Exception:
                    pass


def run_post_acquisition(param_file: Any = None, overrides: Optional[Mapping[str, Any]] = None) -> int:
    try:
        params = _load_params(param_file, overrides)
        session_dir_param = params.get("output_session_folder")
        if not session_dir_param:
            LOG.error("output_session_folder is required")
            return 1
        session_dir = Path(str(session_dir_param)).expanduser().resolve()
        root_name = params.get("behavior_videos_root", _DEF_ROOT)
        behavior_roots = _find_behavior_roots(session_dir, root_name)
        if not behavior_roots:
            LOG.info("No '%s' folders found under %s", root_name, session_dir)
            return 0

        destination_param = params.get("behavior_videos_destination")
        if destination_param:
            dest_base = Path(str(destination_param)).expanduser()
            if not dest_base.is_absolute():
                dest_base = session_dir / dest_base
            else:
                # Default: flatten into session_dir/<behavior_videos_root>
                dest_base = session_dir / root_name
            dest_base.mkdir(parents=True, exist_ok=True)

        exts = params.get("behavior_videos_extensions", list(_DEF_EXTS))
        copy_only = bool(params.get("behavior_videos_copy_only", False))
        remove_empty = bool(params.get("behavior_videos_prune_empty", True))

        flattened: List[str] = []
        for behavior_root in behavior_roots:
            targets = _iter_nested_files(behavior_root, exts)
            if not targets:
                continue

            for src in targets:
                rel = src.relative_to(behavior_root)
                dest = _next_available(dest_base / rel)
                dest.parent.mkdir(parents=True, exist_ok=True)
                if copy_only:
                    shutil.copy2(src, dest)
                else:
                    shutil.move(src, dest)
                flattened.append(dest.relative_to(session_dir).as_posix())
                LOG.info("Flattened %s -> %s", src.relative_to(session_dir), dest.relative_to(session_dir))

            if remove_empty and behavior_root != dest_base:
                _remove_empty_dirs(behavior_root)

        manifest_param = params.get("manifest_path")
        if manifest_param:
            manifest_path = Path(str(manifest_param)).expanduser()
            if not manifest_path.is_absolute():
                manifest_path = session_dir / manifest_path
        else:
            manifest_path = session_dir / "launcher_metadata" / "routing_manifest.json"

        try:
            entries = manifest_utils.read_manifest_entries(manifest_path)
            existing = next((e for e in entries if e.get("type") == "behavior_videos_flattened"), None)
            if existing:
                files = set(existing.get("files", []) or [])
                files.update(flattened)
                existing["files"] = sorted(files)
            else:
                entries.append({"type": "behavior_videos_flattened", "files": sorted(flattened)})
            manifest_utils.write_manifest(manifest_path, entries)
            LOG.info("Registered flattened behavior videos in manifest: %s", manifest_path)
        except Exception as exc:  # noqa: BLE001
            LOG.warning("Could not update manifest %s: %s", manifest_path, exc)

        return 0
    except Exception as exc:  # noqa: BLE001
        LOG.error("Behavior videos flattening failed: %s", exc, exc_info=True)
        return 1
