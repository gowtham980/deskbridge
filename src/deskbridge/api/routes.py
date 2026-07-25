"""HTTP routes for DeskBridge web UI + JSON API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from deskbridge import __version__
from deskbridge.domain.risk import RISK, requires_confirm


def build_router(web_dir: Path) -> APIRouter:
    templates = Jinja2Templates(directory=str(web_dir / "templates"))
    router = APIRouter()

    def service(request: Request):
        return request.app.state.service

    # ---------- pages ----------

    @router.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request) -> HTMLResponse:
        svc = service(request)
        status = svc.run_action("status", source="web")
        latest = svc.audit.latest_screenshot_filename()
        history = svc.history(limit=8)
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "title": "Dashboard",
                "nav": "dashboard",
                "version": __version__,
                "status": status.to_dict(),
                "latest_screenshot": latest,
                "history": history,
                "risk": {k: str(v) for k, v in RISK.items()},
            },
        )

    @router.get("/actions", response_class=HTMLResponse)
    async def actions_page(request: Request) -> HTMLResponse:
        svc = service(request)
        history = svc.history(limit=100)
        return templates.TemplateResponse(
            request,
            "history.html",
            {
                "title": "History",
                "nav": "history",
                "version": __version__,
                "history": history,
            },
        )

    @router.get("/settings", response_class=HTMLResponse)
    async def settings_page(request: Request) -> HTMLResponse:
        svc = service(request)
        settings = svc.config.load()
        status = svc.run_action("status", source="web")
        return templates.TemplateResponse(
            request,
            "settings.html",
            {
                "title": "Settings",
                "nav": "settings",
                "version": __version__,
                "settings": settings.to_dict(),
                "status": status.to_dict(),
                "data_dir": str(svc.data_dir),
            },
        )

    # ---------- API ----------

    @router.get("/api/status")
    async def api_status(request: Request) -> JSONResponse:
        result = service(request).run_action("status", source="api")
        return JSONResponse(result.to_dict(), status_code=200 if result.ok else 400)

    @router.get("/api/history")
    async def api_history(
        request: Request,
        limit: int = Query(50, ge=1, le=500),
        action: str | None = None,
    ) -> dict[str, Any]:
        items = service(request).history(limit=limit, action=action)
        return {"ok": True, "count": len(items), "items": items}

    @router.get("/api/settings")
    async def api_get_settings(request: Request) -> dict[str, Any]:
        settings = service(request).config.load()
        return {"ok": True, "settings": settings.to_dict()}

    @router.post("/api/settings")
    async def api_update_settings(
        request: Request,
        body: dict[str, Any] = Body(default_factory=dict),
    ) -> dict[str, Any]:
        allowed = {"bind_host", "bind_port", "allow_high_risk", "media_retention"}
        updates = {k: v for k, v in body.items() if k in allowed}
        settings = service(request).config.update(**updates)
        return {"ok": True, "settings": settings.to_dict()}

    @router.post("/api/actions/{name}")
    async def api_action(
        name: str,
        request: Request,
        body: dict[str, Any] | None = Body(default=None),
    ) -> JSONResponse:
        payload = dict(body or {})
        confirm = bool(payload.pop("confirm", False) or payload.pop("yes", False))
        if requires_confirm(name) and not confirm:
            return JSONResponse(
                {
                    "ok": False,
                    "action": name,
                    "risk": str(RISK.get(name, "unknown")),
                    "error": f"Action '{name}' requires confirm=true",
                    "code": "confirmation_required",
                    "hint": "Send JSON body {\"confirm\": true} after user confirmation.",
                    "version": __version__,
                },
                status_code=400,
            )
        result = service(request).run_action(
            name,
            payload,
            source="api",
            confirm=confirm,
        )
        return JSONResponse(result.to_dict(), status_code=200 if result.ok else 400)

    @router.get("/media/{filename}")
    async def media_file(filename: str, request: Request) -> FileResponse:
        # Prevent path traversal
        safe = Path(filename).name
        if safe != filename or ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        path = service(request).media / safe
        if not path.exists() or not path.is_file():
            raise HTTPException(status_code=404, detail="Media not found")
        return FileResponse(path, media_type="image/png", filename=safe)

    return router
