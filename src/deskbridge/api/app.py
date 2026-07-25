"""FastAPI application factory."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from deskbridge import __version__
from deskbridge.api.routes import build_router
from deskbridge.paths import default_data_dir
from deskbridge.services.desktop import DesktopService


def create_app(data_dir: Path | None = None) -> FastAPI:
    root = data_dir or default_data_dir()
    service = DesktopService(data_dir=root)

    app = FastAPI(
        title="DeskBridge",
        description="Safe Mac desktop control for OpenClaw — local console + API",
        version=__version__,
    )
    app.state.service = service
    app.state.data_dir = root

    web_dir = Path(__file__).resolve().parent.parent / "web"
    static_dir = web_dir / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    app.include_router(build_router(web_dir))
    return app


def run_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8788,
    reload: bool = False,
    data_dir: Path | None = None,
) -> None:
    import uvicorn

    if data_dir is not None:
        import os

        os.environ["DESKBRIDGE_DATA_DIR"] = str(data_dir)

    # Import string only works well for reload; use factory callable for normal runs
    if reload:
        uvicorn.run(
            "deskbridge.api.app:create_app",
            factory=True,
            host=host,
            port=port,
            reload=True,
            log_level="info",
        )
    else:
        app = create_app(data_dir=data_dir)
        uvicorn.run(app, host=host, port=port, log_level="info")
