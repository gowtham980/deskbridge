"""API smoke tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from deskbridge.api.app import create_app
from deskbridge.platform.darwin import DarwinAdapter
from deskbridge.services.desktop import DesktopService


class FakeAdapter(DarwinAdapter):
    def __init__(self, media_dir: Path) -> None:
        super().__init__(media_dir)

    def require_darwin(self) -> None:
        return

    def status(self) -> dict:
        return {
            "os": "Darwin",
            "hostname": "api-host",
            "battery_percent": 70,
            "permissions": {"screen_recording": "ok", "osascript": "ok"},
            "disk": {
                "size": "500Gi",
                "used": "100Gi",
                "avail": "400Gi",
                "capacity": "20%",
            },
        }

    def screenshot(self, *, display: str = "main", output: str | None = None) -> dict:
        path = self.media_dir / "screenshot-api.png"
        path.write_bytes(b"png")
        return {
            "path": str(path),
            "media": str(path),
            "bytes": 3,
            "display": display,
            "filename": path.name,
        }

    def notify(self, *, title: str, body: str) -> dict:
        return {"title": title, "body": body}


@pytest.fixture()
def client(tmp_path: Path):
    app = create_app(data_dir=tmp_path)
    media = tmp_path / "media"
    media.mkdir(exist_ok=True)
    app.state.service = DesktopService(data_dir=tmp_path, adapter=FakeAdapter(media))
    with TestClient(app) as c:
        yield c


def test_dashboard_loads(client: TestClient):
    r = client.get("/")
    assert r.status_code == 200
    assert "DeskBridge" in r.text
    assert "Quick actions" in r.text


def test_history_page(client: TestClient):
    r = client.get("/actions")
    assert r.status_code == 200
    assert "History" in r.text


def test_settings_page(client: TestClient):
    r = client.get("/settings")
    assert r.status_code == 200


def test_api_status(client: TestClient):
    r = client.get("/api/status")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["hostname"] == "api-host"


def test_api_screenshot(client: TestClient):
    r = client.post("/api/actions/screenshot", json={"display": "main"})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["filename"] == "screenshot-api.png"
    media = client.get(f"/media/{data['filename']}")
    assert media.status_code == 200


def test_api_lock_requires_confirm(client: TestClient):
    r = client.post("/api/actions/lock", json={})
    assert r.status_code == 400
    assert r.json()["code"] == "confirmation_required"


def test_api_history(client: TestClient):
    client.post("/api/actions/notify", json={"title": "t", "body": "b"})
    r = client.get("/api/history")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["count"] >= 1
