"""Service-level tests with temp data dir."""

from __future__ import annotations

from pathlib import Path

import pytest

from deskbridge.domain.errors import DeskBridgeError, ErrorCode
from deskbridge.platform.darwin import DarwinAdapter
from deskbridge.services.desktop import DesktopService


class FakeAdapter(DarwinAdapter):
    def __init__(self, media_dir: Path) -> None:
        super().__init__(media_dir)
        self.calls: list[str] = []

    def require_darwin(self) -> None:
        return

    def status(self) -> dict:
        self.calls.append("status")
        return {
            "os": "Darwin",
            "hostname": "test-host",
            "battery_percent": 50,
            "permissions": {"screen_recording": "ok", "osascript": "ok"},
        }

    def screenshot(self, *, display: str = "main", output: str | None = None) -> dict:
        self.calls.append("screenshot")
        path = Path(output) if output else self.media_dir / "screenshot-test.png"
        path.write_bytes(b"fake-png")
        return {
            "path": str(path),
            "media": str(path),
            "bytes": path.stat().st_size,
            "display": display,
            "filename": path.name,
        }

    def open_app(self, name: str) -> dict:
        self.calls.append(f"open_app:{name}")
        return {"app": "Safari"}

    def quit_app(self, name: str, *, confirm: bool = False) -> dict:
        if not confirm:
            raise DeskBridgeError(
                "Refusing to quit without confirm",
                code=ErrorCode.CONFIRMATION_REQUIRED,
            )
        return {"app": name}

    def lock(self, *, confirm: bool = False) -> dict:
        if not confirm:
            raise DeskBridgeError(
                "Refusing to lock without confirm",
                code=ErrorCode.CONFIRMATION_REQUIRED,
            )
        return {"method": "fake", "message": "locked"}

    def get_volume(self) -> dict:
        return {"output_volume": 40, "muted": False}

    def set_volume(self, level: int) -> dict:
        return {"level": level, "result": {"output_volume": level, "muted": False}}


@pytest.fixture()
def svc(tmp_path: Path) -> DesktopService:
    media = tmp_path / "media"
    media.mkdir()
    adapter = FakeAdapter(media)
    return DesktopService(data_dir=tmp_path, adapter=adapter)


def test_status_ok(svc: DesktopService):
    result = svc.run_action("status", source="test")
    assert result.ok is True
    assert result.to_dict()["hostname"] == "test-host"


def test_screenshot_audited(svc: DesktopService):
    result = svc.run_action("screenshot", {"display": "main"}, source="test")
    assert result.ok is True
    assert "screenshot" in result.to_dict().get("filename", "")
    hist = svc.history(limit=5)
    assert hist
    assert hist[0]["action"] == "screenshot"
    assert hist[0]["ok"] is True


def test_quit_requires_confirm(svc: DesktopService):
    result = svc.run_action("quit-app", {"name": "Music"}, source="test", confirm=False)
    assert result.ok is False
    assert result.code == ErrorCode.CONFIRMATION_REQUIRED


def test_lock_with_confirm(svc: DesktopService):
    result = svc.run_action("lock", source="test", confirm=True)
    assert result.ok is True


def test_unknown_action(svc: DesktopService):
    result = svc.run_action("explode", source="test")
    assert result.ok is False
