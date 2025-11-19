"""Session archiver post-acquisition module.

This module copies files produced during a session to a network
location, verifies integrity, and then relocates the originals to a
backup/delete directory so they can be safely removed later. It keeps a
manifest to allow safe retries after interruptions.
"""
from __future__ import annotations

import json
import logging
import shutil
import tempfile
from datetime import datetime, timezone
from fnmatch import fnmatch
from hashlib import new as new_hash
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional, Union

from openscope_experimental_launcher.utils import param_utils

LOG = logging.getLogger(__name__)


class SessionArchiver:
    """Move session output to a network path with verification."""

    def __init__(
        self,
        session_dir: Path,
        network_dir: Path,
        backup_dir: Path,
        *,
        manifest_path: Path,
        checksum_algo: str = "sha256",
        include_patterns: Iterable[str] = ("*",),
        exclude_patterns: Iterable[str] = (),
        dry_run: bool = False,
        skip_completed: bool = True,
        max_retries: int = 2,
        remove_empty_dirs: bool = False,
        enable_network_copy: bool = True,
        enable_backup_move: bool = True,
    ) -> None:
        self.session_dir = session_dir
        self.network_dir = network_dir
        self.backup_dir = backup_dir
        self.manifest_path = manifest_path
        self.checksum_algo = checksum_algo
        self.include_patterns = self._normalize_patterns(include_patterns, default="*")
        self.exclude_patterns = self._normalize_patterns(exclude_patterns)
        self.dry_run = dry_run
        self.skip_completed = skip_completed
        self.max_retries = max(0, max_retries)
        self.remove_empty_dirs = remove_empty_dirs
        self.enable_network_copy = bool(enable_network_copy)
        self.enable_backup_move = bool(enable_backup_move)

        self._manifest: Dict[str, Any] = {}
        if self.manifest_path.exists():
            self._load_manifest()
        else:
            self._manifest = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "session_dir": str(self.session_dir),
                "network_dir": str(self.network_dir),
                "backup_dir": str(self.backup_dir),
                "files": {},
            }

        self.successful = 0
        self.failed = 0

    def run(self) -> None:
        for file_path in self._iter_session_files():
            rel_path = file_path.relative_to(self.session_dir)
            rel_key = rel_path.as_posix()

            if self.skip_completed and self._manifest["files"].get(rel_key, {}).get("status") == "complete":
                LOG.info("Skipping previously archived file '%s'", rel_key)
                continue

            try:
                self._process_single_file(file_path, rel_path)
                self.successful += 1
            except Exception as exc:  # noqa: BLE001
                self.failed += 1
                LOG.error("Failed to archive '%s': %s", rel_key, exc, exc_info=True)
                self._mark_file(rel_key, status="error", error=str(exc))

        if self.remove_empty_dirs and not self.dry_run:
            self._prune_empty_directories()

    @staticmethod
    def _normalize_patterns(patterns: Iterable[str] | None, *, default: Optional[str] = None) -> list[str]:
        if patterns is None:
            return [default] if default else []
        if isinstance(patterns, str):
            return [patterns]
        normalized = [pat for pat in patterns if pat]
        if not normalized and default:
            normalized.append(default)
        return normalized

    def _iter_session_files(self) -> Iterable[Path]:
        for path in self.session_dir.rglob("*"):
            if path.is_file() and self._should_transfer(path):
                yield path

    def _should_transfer(self, path: Path) -> bool:
        rel = path.relative_to(self.session_dir).as_posix()
        if any(fnmatch(rel, pattern) or fnmatch(path.name, pattern) for pattern in self.exclude_patterns):
            return False
        if not self.include_patterns:
            return True
        return any(fnmatch(rel, pattern) or fnmatch(path.name, pattern) for pattern in self.include_patterns)

    def _process_single_file(self, source: Path, rel_path: Path) -> None:
        rel_key = rel_path.as_posix()
        dest_path = self.network_dir / rel_path if self.enable_network_copy else None
        backup_path = self.backup_dir / rel_path if self.enable_backup_move else None

        LOG.info("Transferring '%s'", rel_key)

        if not self.enable_network_copy and not self.enable_backup_move:
            LOG.info("Network and backup transfers disabled; skipping '%s'", rel_key)
            self._mark_file(
                rel_key,
                status="skipped",
                network_copy=False,
                backup_move=False,
                reason="transfers_disabled",
            )
            return

        if self.dry_run:
            LOG.info("Dry run enabled; skipping copy and move for '%s'", rel_key)
            self._mark_file(
                rel_key,
                status="skipped",
                network_copy=self.enable_network_copy,
                backup_move=self.enable_backup_move,
            )
            return

        retries = 0
        while True:
            try:
                checksum = self._compute_digest(source)
                entry_fields: Dict[str, Any] = {
                    "checksum": checksum,
                    "network_copy": self.enable_network_copy,
                    "backup_move": self.enable_backup_move,
                }

                if self.enable_network_copy:
                    if dest_path is None:
                        raise ValueError("Destination path unavailable for network copy")
                    self._copy_with_temp(source, dest_path)
                    checksum = self._verify_checksum(source, dest_path)
                    entry_fields["checksum"] = checksum
                    entry_fields["network_path"] = str(dest_path)

                if self.enable_backup_move:
                    if backup_path is None:
                        raise ValueError("Backup path unavailable for original relocation")
                    self._relocate_original(source, backup_path)
                    entry_fields["backup_path"] = str(backup_path)
                else:
                    LOG.info("Backup move disabled; retaining original file '%s'", rel_key)

                self._mark_file(rel_key, status="complete", **entry_fields)
                break
            except Exception:  # noqa: BLE001
                retries += 1
                if retries > self.max_retries:
                    raise
                LOG.warning(
                    "Retrying transfer for '%s' (%s/%s)",
                    rel_key,
                    retries,
                    self.max_retries,
                    exc_info=True,
                )

    def _copy_with_temp(self, src: Path, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(delete=False, dir=dest.parent, prefix=".tmp_copy_", suffix=dest.suffix) as tmp:
            temp_path = Path(tmp.name)
        try:
            shutil.copy2(src, temp_path)
            temp_path.replace(dest)
        finally:
            if temp_path.exists() and not dest.exists():
                temp_path.unlink(missing_ok=True)

    def _verify_checksum(self, src: Path, dest: Path) -> str:
        src_hash = self._compute_digest(src)
        dest_hash = self._compute_digest(dest)
        if src_hash != dest_hash:
            raise IOError(f"Checksum mismatch for '{src}' (expected {src_hash}, got {dest_hash})")
        return src_hash

    def _compute_digest(self, file_path: Path, chunk_size: int = 1024 * 1024) -> str:
        try:
            hasher = new_hash(self.checksum_algo)
        except ValueError as exc:  # unknown algorithm
            raise ValueError(f"Unsupported checksum algorithm: {self.checksum_algo}") from exc
        with file_path.open("rb") as handle:
            while data := handle.read(chunk_size):
                hasher.update(data)
        return hasher.hexdigest()

    def _relocate_original(self, src: Path, backup_path: Path) -> None:
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(src, backup_path)

    def _mark_file(self, rel_key: str, *, status: str, **fields: Any) -> None:
        entry = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        entry.update(fields)
        self._manifest.setdefault("files", {})[rel_key] = entry
        self._manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._persist_manifest()

    def _load_manifest(self) -> None:
        with self.manifest_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("Manifest format invalid: expected JSON object")
        self._manifest.update(data)
        self._manifest.setdefault("files", {})
        LOG.info("Loaded existing manifest with %s entries", len(self._manifest["files"]))

    def _persist_manifest(self) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            dir=self.manifest_path.parent,
            prefix=".manifest_",
            suffix=".json",
            encoding="utf-8",
        ) as tmp:
            json.dump(self._manifest, tmp, indent=2)
            tmp.flush()
            temp_path = Path(tmp.name)
        temp_path.replace(self.manifest_path)

    def _prune_empty_directories(self) -> None:
        directories = {
            p
            for p in self.session_dir.rglob("*")
            if p.is_dir()
        }
        for directory in sorted(
            directories,
            key=lambda path: len(path.relative_to(self.session_dir).parts),
            reverse=True,
        ):
            if directory == self.session_dir:
                continue
            try:
                if not any(directory.iterdir()):
                    directory.rmdir()
                    LOG.info("Removed empty directory '%s'", directory)
            except OSError:
                continue


def run_post_acquisition(
    param_file: Union[str, Dict[str, Any]],
    overrides: Optional[Dict[str, Any]] = None,
) -> int:
    required_fields = ["session_dir", "network_dir", "backup_dir"]
    defaults = {
        "include_patterns": ["*"],
        "exclude_patterns": [],
        "checksum_algo": "sha256",
        "dry_run": False,
        "skip_completed": True,
        "max_retries": 2,
        "remove_empty_dirs": False,
    }
    help_texts = {
        "session_dir": "Path to the session output folder to archive",
        "network_dir": "Network destination where files will be copied",
        "backup_dir": "Local directory where originals are moved after verification",
    }

    prompt_func: Callable[..., Any] = param_utils.get_user_input
    merged_overrides: Dict[str, Any] = {}

    if isinstance(param_file, dict):
        merged_overrides.update(param_file)
    if overrides:
        merged_overrides.update(overrides)

    if "prompt_func" in merged_overrides:
        prompt_func = merged_overrides["prompt_func"]

    clean_overrides = {k: v for k, v in merged_overrides.items() if k != "prompt_func"}

    param_path: Optional[str]
    if isinstance(param_file, str):
        param_path = param_file
    else:
        maybe_path = merged_overrides.get("param_file")
        param_path = maybe_path if isinstance(maybe_path, str) else None

    params = param_utils.load_parameters(
        param_file=param_path,
        overrides=clean_overrides,
        required_fields=required_fields,
        defaults=defaults,
        help_texts=help_texts,
        prompt_func=prompt_func,
    )

    params.pop("prompt_func", None)

    def _prompt_value(message: str, default_value: Any) -> Any:
        try:
            return prompt_func(message, default_value)
        except TypeError:
            try:
                return prompt_func(message, default_value, type(default_value))
            except TypeError:
                return default_value
        except KeyboardInterrupt:
            raise
        except Exception:
            LOG.info("Input not available for prompt '%s'; using default '%s'", message, default_value)
            return default_value

    def _interpret_bool(value: Any, fallback: bool) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return fallback
        text = str(value).strip().lower()
        if not text:
            return fallback
        if text in {"y", "yes", "true", "1"}:
            return True
        if text in {"n", "no", "false", "0"}:
            return False
        return fallback

    def _prompt_bool(message: str, default: bool = True) -> bool:
        default_token = "yes" if default else "no"
        response = _prompt_value(message, default_token)
        return _interpret_bool(response, default)

    def _prompt_path(message: str, current_value: Path) -> Path:
        response = _prompt_value(message, str(current_value))
        if response is None:
            return current_value
        text = str(response).strip()
        if not text:
            return current_value
        return Path(text).expanduser()

    base_session = params.get("session_dir") or params.get("output_session_folder")
    if not base_session:
        LOG.error("Parameter 'session_dir' missing and no output_session_folder available")
        return 2
    session_dir = Path(base_session).expanduser().resolve()

    network_path = params.get("network_dir")
    backup_path = params.get("backup_dir")
    if not network_path or not backup_path:
        LOG.error("Parameters 'network_dir' and 'backup_dir' are required for session archiving")
        return 2

    network_dir = _prompt_path("Confirm network archive directory", Path(str(network_path)).expanduser())
    backup_dir = _prompt_path("Confirm backup directory for originals", Path(str(backup_path)).expanduser())

    params["network_dir"] = str(network_dir)
    params["backup_dir"] = str(backup_dir)

    move_to_network = _prompt_bool(f"Move data to network destination '{network_dir}'?", True)
    move_to_backup = _prompt_bool(f"Move data to backup location '{backup_dir}'?", True)

    LOG.info(
        "Transfer confirmations -> network: %s | backup: %s",
        "enabled" if move_to_network else "disabled",
        "enabled" if move_to_backup else "disabled",
    )

    manifest_value = params.get("manifest_path") or (backup_dir / "session_archiver_manifest.json")
    manifest_path = Path(manifest_value).expanduser()

    LOG.info("Starting session archiver")

    if not session_dir.exists():
        LOG.error("Session directory does not exist: %s", session_dir)
        return 2

    if move_to_network:
        try:
            network_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            LOG.error("Cannot access network directory '%s': %s", network_dir, exc)
            return 2
    else:
        LOG.info("Network transfer disabled; skipping network directory creation")

    if move_to_backup:
        backup_dir.mkdir(parents=True, exist_ok=True)
    else:
        LOG.info("Backup transfer disabled; originals will remain in session directory")

    include_patterns = params.get("include_patterns", defaults["include_patterns"])
    exclude_patterns = params.get("exclude_patterns", defaults["exclude_patterns"])

    archiver = SessionArchiver(
        session_dir=session_dir,
        network_dir=network_dir,
        backup_dir=backup_dir,
        manifest_path=manifest_path,
        checksum_algo=params.get("checksum_algo", defaults["checksum_algo"]),
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        dry_run=bool(params.get("dry_run", defaults["dry_run"])),
        skip_completed=bool(params.get("skip_completed", defaults["skip_completed"])),
        max_retries=int(params.get("max_retries", defaults["max_retries"])),
        remove_empty_dirs=bool(
            params.get("remove_empty_dirs", defaults["remove_empty_dirs"])
        ),
        enable_network_copy=move_to_network,
        enable_backup_move=move_to_backup,
    )

    LOG.info("Session directory: %s", session_dir)
    LOG.info("Network directory: %s", network_dir)
    LOG.info("Backup directory: %s", backup_dir)
    LOG.info("Manifest path: %s", manifest_path)
    LOG.info("Dry run: %s | Checksum: %s | Retries: %s", archiver.dry_run, archiver.checksum_algo, archiver.max_retries)
    LOG.info("Include patterns: %s", archiver.include_patterns)
    LOG.info("Exclude patterns: %s", archiver.exclude_patterns)
    LOG.info(
        "Effective transfers -> network: %s | backup: %s",
        "enabled" if archiver.enable_network_copy else "disabled",
        "enabled" if archiver.enable_backup_move else "disabled",
    )

    try:
        archiver.run()
    except KeyboardInterrupt:
        LOG.warning("Archival interrupted by user")
        return 1
    except Exception as exc:  # noqa: BLE001
        LOG.error("Archival failed: %s", exc, exc_info=True)
        return 2

    LOG.info(
        "Archive complete. Success: %s, Failed: %s", archiver.successful, archiver.failed
    )
    return 0 if archiver.failed == 0 else 3
