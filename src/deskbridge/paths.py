"""Application data paths for DeskBridge."""

from __future__ import annotations

import os
from pathlib import Path


def default_data_dir() -> Path:
    override = os.environ.get("DESKBRIDGE_DATA_DIR")
    if override:
        path = Path(override).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    if os.name == "posix":
        base = Path.home() / "Library" / "Application Support" / "DeskBridge"
    else:
        base = Path.home() / ".deskbridge"
    base.mkdir(parents=True, exist_ok=True)
    return base


def db_path(data_dir: Path | None = None) -> Path:
    root = data_dir or default_data_dir()
    root.mkdir(parents=True, exist_ok=True)
    return root / "deskbridge.db"


def media_dir(data_dir: Path | None = None) -> Path:
    root = data_dir or default_data_dir()
    path = root / "media"
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_path(data_dir: Path | None = None) -> Path:
    root = data_dir or default_data_dir()
    root.mkdir(parents=True, exist_ok=True)
    return root / "settings.json"
