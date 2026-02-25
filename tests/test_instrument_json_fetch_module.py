from __future__ import annotations

import builtins
import os
from pathlib import Path

from openscope_experimental_launcher.pre_acquisition import instrument_json_fetch


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_copies_latest_instrument_json_when_assume_yes(tmp_path):
    source_root = tmp_path / "slap2_processing"
    older = source_root / "a" / "instrument.json"
    newer = source_root / "b" / "instrument.json"

    _write(older, "{\"name\": \"older\"}\n")
    _write(newer, "{\"name\": \"newer\"}\n")

    os.utime(older, (1, 1))
    os.utime(newer, (10, 10))

    session_dir = tmp_path / "session"
    session_dir.mkdir()

    params = {
        "output_session_folder": str(session_dir),
        "assume_yes": True,
        "instrument_json_source_root": str(source_root),
        "instrument_json_required": True,
    }

    exit_code = instrument_json_fetch.run_pre_acquisition(params)
    assert exit_code == 0

    dest = session_dir / "instrument.json"
    assert dest.exists()
    assert "newer" in dest.read_text(encoding="utf-8")


def test_operator_can_override_source_path(tmp_path, monkeypatch):
    source_root = tmp_path / "slap2_processing"
    found = source_root / "instrument.json"
    alternate = tmp_path / "alternate" / "instrument.json"

    _write(found, "{\"name\": \"found\"}\n")
    _write(alternate, "{\"name\": \"alternate\"}\n")

    session_dir = tmp_path / "session"
    session_dir.mkdir()

    replies = iter(
        [
            # Decline the found candidate
            "n",
            # Provide alternate path
            str(alternate),
        ]
    )

    def fake_input(prompt: str) -> str:
        return next(replies)

    monkeypatch.setattr(builtins, "input", fake_input)

    params = {
        "output_session_folder": str(session_dir),
        "assume_yes": False,
        "instrument_json_source_root": str(source_root),
        "instrument_json_required": True,
    }

    exit_code = instrument_json_fetch.run_pre_acquisition(params)
    assert exit_code == 0

    dest = session_dir / "instrument.json"
    assert dest.exists()
    assert "alternate" in dest.read_text(encoding="utf-8")
