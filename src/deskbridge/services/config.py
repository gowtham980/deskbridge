"""Settings persistence."""

from __future__ import annotations

import json
from pathlib import Path

from deskbridge.domain.models import Settings
from deskbridge.paths import default_data_dir, settings_path


class ConfigService:
    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or default_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = settings_path(self.data_dir)

    def load(self) -> Settings:
        if not self.path.exists():
            settings = Settings(data_dir=str(self.data_dir))
            self.save(settings)
            return settings
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return Settings(data_dir=str(self.data_dir))
        settings = Settings.from_dict(raw)
        if not settings.data_dir:
            settings.data_dir = str(self.data_dir)
        return settings

    def save(self, settings: Settings) -> Settings:
        if not settings.data_dir:
            settings.data_dir = str(self.data_dir)
        payload = settings.to_dict()
        self.path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return settings

    def update(self, **kwargs: object) -> Settings:
        settings = self.load()
        for key, value in kwargs.items():
            if hasattr(settings, key) and value is not None:
                setattr(settings, key, value)
        return self.save(settings)
