"""Annotate and normalize SLAP2 behavior videos into the AIND behavior-videos layout.

Steps:
- Discover *.avi files produced by Bonsai under the session folder.
- Discover SoftwareEvents JSON logs for each camera to populate metadata.
- For each video, create behavior-videos/<CameraName>/video.avi and metadata.csv
  with ReferenceTime, CameraFrameNumber, CameraFrameTime columns.
"""

from __future__ import annotations

import csv
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from openscope_experimental_launcher.utils import param_utils
from openscope_experimental_launcher.utils import manifest_utils

LOG = logging.getLogger(__name__)


def _discover_event_logs(session_dir: Path) -> Dict[str, Path]:
    mapping: Dict[str, Path] = {}
    for events_dir in session_dir.rglob("SoftwareEvents"):
        for json_file in events_dir.glob("*.json"):
            key = json_file.stem.lower()
            if key not in mapping:
                mapping[key] = json_file
    return mapping


def _select_event_file(camera_name: str, event_map: Dict[str, Path]) -> Path | None:
    key = camera_name.lower()
    if key in event_map:
        return event_map[key]
    for candidate_key, path in event_map.items():
        if key in candidate_key or candidate_key in key:
            return path


        def _collect_launcher_metadata(session_dir: Path) -> List[str]:
            metadata_dir = session_dir / "launcher_metadata"
            if not metadata_dir.exists():
                return []
            return [p.relative_to(session_dir).as_posix() for p in metadata_dir.rglob("*") if p.is_file()]
    return None


def _load_event_rows(event_path: Path) -> List[Tuple[Any, Any, Any]]:
    rows: List[Tuple[Any, Any, Any]] = []
    with event_path.open(encoding="utf-8") as handle:
        for idx, line in enumerate(handle):
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                LOG.warning("Skipping invalid JSON line %s in %s", idx, event_path)
                continue
            data = payload.get("data") or {}
            # ReferenceTime is unknown from SoftwareEvents; emit empty.
            ref_time = ""
            # CameraFrameNumber should be the zero-based index in the log.
            frame_num = idx
            # CameraFrameTime comes from the Bonsai timestamp fields.
            frame_time = payload.get("frame_timestamp")
            if frame_time is None:
                frame_time = data.get("FrameTime") or data.get("frame_time")
            if frame_time is None:
                frame_time = payload.get("timestamp") or data.get("timestamp")
            rows.append((ref_time, frame_num, frame_time))
    return rows


def _write_metadata_csv(csv_path: Path, rows: Sequence[Tuple[Any, Any, Any]]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ReferenceTime", "CameraFrameNumber", "CameraFrameTime"])
        for ref_time, frame_num, frame_time in rows:
            writer.writerow([ref_time, frame_num, frame_time])
def _unique_container_name(base: str, used: set[str], root: Path) -> str:
    safe = base.replace(" ", "_")
    candidate = safe
    counter = 2
    while candidate in used or (root / candidate).exists():
        candidate = f"{safe}_{counter:02d}"
        counter += 1
    return candidate


def _build_camera_name_map(params: Dict[str, Any]) -> Dict[str, str]:
    default_map = {
        "bodycamera": "BodyCamera",
        "body_cam": "BodyCamera",
        "body": "BodyCamera",
        "facecamera": "FaceCamera",
        "face_cam": "FaceCamera",
        "face": "FaceCamera",
        "eyecamera": "EyeCamera",
        "eye_cam": "EyeCamera",
        "eye": "EyeCamera",
    }
    user_map = params.get("camera_name_map") or {}
    name_map: Dict[str, str] = {k.lower(): v for k, v in default_map.items()}
    if isinstance(user_map, dict):
        name_map.update({str(k).lower(): str(v) for k, v in user_map.items()})
    return name_map


def _normalize_camera_name(stem: str, name_map: Dict[str, str]) -> str:
    key = stem.lower()
    key_stripped = "".join(ch for ch in key if ch.isalnum())
    for candidate in (key, key_stripped):
        if candidate in name_map:
            return name_map[candidate]
    for alias, canonical in name_map.items():
        if alias in key or alias in key_stripped:
            return canonical
    return stem


def run(params: Dict[str, Any]) -> int:
    if params is None:
        params = {}
    elif not isinstance(params, dict):
        LOG.warning("slap2_behaviorvideo_annotator received non-dict params; interpreting as session dir")
        params = {"output_session_folder": params}

    session_dir_param = params.get("output_session_folder")
    if not session_dir_param:
        LOG.error("output_session_folder is required for slap2_behaviorvideo_annotator")
        return 2
    session_dir = Path(str(session_dir_param)).expanduser().resolve()

    assume_yes = bool(params.get("assume_yes", False))
    behavior_videos_dir = params.get("behavior_videos_dir", "behavior-videos")
    manifest_name = params.get("manifest_name", "routing_manifest.json")

    manifest_path_param = params.get("manifest_path")
    if manifest_path_param:
        manifest_path_obj = Path(str(manifest_path_param)).expanduser()
        routing_manifest_path = (
            manifest_path_obj if manifest_path_obj.is_absolute() else session_dir / manifest_path_obj
        )
    else:
        routing_manifest_path = session_dir / "launcher_metadata" / manifest_name

    if not session_dir.exists():
        LOG.error("Session directory does not exist: %s", session_dir)
        return 2

    avi_files = sorted(session_dir.rglob("*.avi"))
    if not avi_files:
        LOG.warning("No .avi files found under %s", session_dir)
        return 0

    event_map = _discover_event_logs(session_dir)
    name_map = _build_camera_name_map(params)
    used_names: set[str] = set()
    entries: List[Dict[str, Any]] = []
    existing_entries: List[Dict[str, Any]] = manifest_utils.read_manifest_entries(routing_manifest_path)

    for avi_path in avi_files:
        camera_name = _normalize_camera_name(avi_path.stem, name_map)
        container_name = _unique_container_name(camera_name, used_names, session_dir / behavior_videos_dir)
        used_names.add(container_name)

        dest_dir = session_dir / behavior_videos_dir / container_name
        dest_video = dest_dir / f"video{avi_path.suffix}"
        metadata_path = dest_dir / "metadata.csv"

        event_file = _select_event_file(camera_name, event_map)
        rows: List[Tuple[Any, Any, Any]] = []
        if event_file and event_file.exists():
            rows = _load_event_rows(event_file)
        else:
            LOG.warning("No SoftwareEvents file found for %s; writing empty metadata", camera_name)

        LOG.info(
            "Prepared behavior video package | camera=%s | src=%s | dest=%s | events=%s",
            camera_name,
            avi_path.relative_to(session_dir),
            dest_dir.relative_to(session_dir),
            event_file.name if event_file else "none",
        )

        proceed = True
        if not assume_yes:
            try:
                confirm = param_utils.get_user_input("Proceed with move and metadata? (y/N)", "n")
            except Exception:
                confirm = "n"
            proceed = str(confirm).lower() in {"y", "yes"}
        if not proceed:
            LOG.info("Operator declined processing for %s", avi_path)
            continue

        dest_dir.mkdir(parents=True, exist_ok=True)
        _write_metadata_csv(metadata_path, rows)
        final_video_path = dest_video
        if final_video_path.exists():
            final_video_path = final_video_path.with_name(final_video_path.stem + "_dup" + final_video_path.suffix)
        shutil.move(str(avi_path), final_video_path)

        LOG.info(
            "Behavior video packaged | camera=%s | video=%s | metadata=%s",
            container_name,
            final_video_path.relative_to(session_dir),
            metadata_path.relative_to(session_dir),
        )

        file_list = [
            final_video_path.relative_to(session_dir).as_posix(),
            metadata_path.relative_to(session_dir).as_posix(),
        ]
        if event_file:
            file_list.append(event_file.relative_to(session_dir).as_posix())

        entries.append(
            {
                "container": container_name,
                "source_video": avi_path.relative_to(session_dir).as_posix(),
                "dest_dir": dest_dir.relative_to(session_dir).as_posix(),
                "video": final_video_path.relative_to(session_dir).as_posix(),
                "metadata": metadata_path.relative_to(session_dir).as_posix(),
                "event_file": event_file.relative_to(session_dir).as_posix() if event_file else "",
                "files": file_list,
            }
        )

    if entries:
        combined_entries = existing_entries + entries
        metadata_files = _collect_launcher_metadata(session_dir)
        if metadata_files:
            existing_metadata = next((e for e in combined_entries if e.get("type") == "launcher_metadata"), None)
            if existing_metadata:
                merged = set(existing_metadata.get("files", []) or [])
                merged.update(metadata_files)
                existing_metadata["files"] = sorted(merged)
            else:
                combined_entries.append({"type": "launcher_metadata", "files": sorted(set(metadata_files))})
        manifest_utils.write_manifest(routing_manifest_path, combined_entries)
        LOG.info("Behavior video manifest written: %s", routing_manifest_path)

    return 0
def run_post_acquisition(param_file: Union[str, Dict[str, Any]], overrides: Optional[Dict[str, Any]] = None) -> int:
    try:
        if isinstance(param_file, dict):
            # Allow the launcher to pass params directly without hitting the filesystem
            params = dict(param_file)
            if overrides:
                params.update(overrides)
        else:
            params = param_utils.load_parameters(param_file=param_file, overrides=overrides)
        return run(params)
    except Exception as exc:  # noqa: BLE001
        LOG.error("Behavior video annotation failed: %s", exc, exc_info=True)
        return 1
