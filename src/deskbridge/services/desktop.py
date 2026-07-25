"""Desktop orchestration service — risk checks, audit, adapter calls."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Callable

from deskbridge import __version__
from deskbridge.domain.errors import DeskBridgeError, ErrorCode
from deskbridge.domain.models import ActionRecord, ActionResult
from deskbridge.domain.risk import RISK, requires_confirm, risk_for
from deskbridge.paths import db_path, default_data_dir, media_dir
from deskbridge.platform.darwin import DarwinAdapter
from deskbridge.services.audit import AuditService
from deskbridge.services.config import ConfigService


class DesktopService:
    """High-level action runner shared by CLI and HTTP API."""

    def __init__(
        self,
        *,
        data_dir: Path | None = None,
        adapter: DarwinAdapter | None = None,
        audit: AuditService | None = None,
        config: ConfigService | None = None,
    ) -> None:
        self.data_dir = data_dir or default_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.media = media_dir(self.data_dir)
        self.config = config or ConfigService(self.data_dir)
        self.audit = audit or AuditService(db_path(self.data_dir))
        self.adapter = adapter or DarwinAdapter(self.media)

    def supported_actions(self) -> list[str]:
        return sorted(RISK.keys())

    def history(
        self,
        *,
        limit: int = 50,
        action: str | None = None,
        ok: bool | None = None,
    ) -> list[dict[str, Any]]:
        return [
            r.to_dict()
            for r in self.audit.list(limit=limit, action=action, ok=ok)
        ]

    def cleanup_media(self, keep: int | None = None) -> int:
        settings = self.config.load()
        retention = keep if keep is not None else settings.media_retention
        files = sorted(
            self.media.glob("screenshot-*.png"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        removed = 0
        for path in files[retention:]:
            try:
                path.unlink(missing_ok=True)
                removed += 1
            except OSError:
                pass
        return removed

    def run_action(
        self,
        action: str,
        params: dict[str, Any] | None = None,
        *,
        source: str = "api",
        confirm: bool = False,
    ) -> ActionResult:
        params = dict(params or {})
        risk = risk_for(action)

        # High-risk gate via settings
        settings = self.config.load()
        if str(risk) == "high" and not settings.allow_high_risk and action != "history":
            result = ActionResult(
                ok=False,
                action=action,
                risk=risk,
                version=__version__,
                error="High-risk actions are disabled in settings",
                code=ErrorCode.CONFIRMATION_REQUIRED,
                hint="Enable allow_high_risk in Settings or use low/medium actions only.",
            )
            self._audit(action, params, result, source)
            return result

        try:
            data = self._dispatch(action, params, confirm=confirm)
            message = None
            if isinstance(data, dict) and "message" in data:
                message = str(data.pop("message"))
            # Default messages
            if message is None:
                message = self._default_message(action, data)
            result = ActionResult(
                ok=True,
                action=action,
                risk=risk,
                version=__version__,
                message=message,
                data=data if isinstance(data, dict) else {"result": data},
            )
            if action == "screenshot":
                self.cleanup_media()
        except DeskBridgeError as exc:
            result = ActionResult(
                ok=False,
                action=action,
                risk=risk,
                version=__version__,
                error=exc.message,
                code=exc.code,
                hint=exc.hint,
                data=exc.extra,
            )
        except subprocess.TimeoutExpired:
            result = ActionResult(
                ok=False,
                action=action,
                risk=risk,
                version=__version__,
                error="Command timed out",
                code=ErrorCode.TIMEOUT,
            )
        except Exception as exc:  # noqa: BLE001
            result = ActionResult(
                ok=False,
                action=action,
                risk=risk,
                version=__version__,
                error=str(exc),
                code=ErrorCode.INTERNAL_ERROR,
            )

        self._audit(action, params, result, source)
        return result

    def _audit(
        self,
        action: str,
        params: dict[str, Any],
        result: ActionResult,
        source: str,
    ) -> None:
        # Avoid logging full clipboard contents in params
        safe_params = dict(params)
        if action == "clipboard-set" and "text" in safe_params:
            text = str(safe_params.get("text") or "")
            safe_params["text"] = f"<{len(text)} chars>"
        if action == "clipboard-get" and result.ok:
            # keep length only in stored result for privacy-ish audit
            stored = result.to_dict()
            if "text" in stored:
                stored["text"] = f"<{stored.get('length', '?')} chars>"
            payload = stored
        else:
            payload = result.to_dict()

        record = ActionRecord.create(
            action=action,
            params=safe_params,
            risk=str(result.risk),
            ok=result.ok,
            result=payload,
            error=result.error,
            source=source,
        )
        self.audit.add(record)

    def _default_message(self, action: str, data: dict[str, Any]) -> str | None:
        if action == "open-app":
            return f"Opened {data.get('app')}"
        if action == "open-url":
            return f"Opened {data.get('url')}"
        if action == "focus-app":
            return f"Focused {data.get('app')}"
        if action == "quit-app":
            return f"Quit {data.get('app')}"
        if action == "mute":
            return "Muted"
        if action == "unmute":
            return "Unmuted"
        if action == "volume" and "level" in data:
            return f"Volume set to {data.get('level')}"
        if action == "notify":
            return "Notification sent"
        if action == "screenshot":
            return f"Screenshot saved to {data.get('path')}"
        if action == "clipboard-set":
            return "Clipboard updated"
        if action == "sleep-display":
            return "Display sleep requested"
        if action == "lock":
            return str(data.get("message") or "Lock requested")
        return None

    def _dispatch(
        self,
        action: str,
        params: dict[str, Any],
        *,
        confirm: bool,
    ) -> dict[str, Any]:
        handlers: dict[str, Callable[[], dict[str, Any]]] = {
            "status": lambda: {
                **self.adapter.status(),
                "supported_actions": self.supported_actions(),
                "data_dir": str(self.data_dir),
            },
            "screenshot": lambda: self.adapter.screenshot(
                display=str(params.get("display") or "main"),
                output=params.get("output"),
            ),
            "open-app": lambda: self.adapter.open_app(str(params.get("name") or "")),
            "open-url": lambda: self.adapter.open_url(str(params.get("url") or "")),
            "list-apps": lambda: self.adapter.list_apps(),
            "focus-app": lambda: self.adapter.focus_app(str(params.get("name") or "")),
            "quit-app": lambda: self.adapter.quit_app(
                str(params.get("name") or ""),
                confirm=confirm or bool(params.get("yes")),
            ),
            "volume": lambda: self._volume(params),
            "mute": lambda: self.adapter.mute(),
            "unmute": lambda: self.adapter.unmute(),
            "notify": lambda: self.adapter.notify(
                title=str(params.get("title") or "DeskBridge"),
                body=str(params.get("body") or params.get("message") or ""),
            ),
            "sleep-display": lambda: self.adapter.sleep_display(
                confirm=confirm or bool(params.get("yes"))
            ),
            "lock": lambda: self.adapter.lock(
                confirm=confirm or bool(params.get("yes"))
            ),
            "clipboard-get": lambda: self.adapter.clipboard_get(),
            "clipboard-set": lambda: self.adapter.clipboard_set(
                str(params.get("text") if params.get("text") is not None else "")
            ),
            "history": lambda: {
                "items": self.history(
                    limit=int(params.get("limit") or 50),
                    action=params.get("action"),
                )
            },
        }
        handler = handlers.get(action)
        if not handler:
            raise DeskBridgeError(
                f"Unknown action: {action}",
                code=ErrorCode.UNKNOWN_ACTION,
            )
        # Double-check confirm for policy-listed actions when caller forgot
        if requires_confirm(action) and not (confirm or bool(params.get("yes"))):
            # Let adapter raise for consistency on quit/lock/sleep — but still guard
            pass
        return handler()

    def _volume(self, params: dict[str, Any]) -> dict[str, Any]:
        if params.get("get") or params.get("level") is None:
            if params.get("level") is None and not params.get("get"):
                # default to get when neither provided for agent friendliness
                if "level" not in params:
                    return {"result": self.adapter.get_volume()}
            if params.get("get") and params.get("level") is None:
                return {"result": self.adapter.get_volume()}
            if params.get("level") is None:
                raise DeskBridgeError(
                    "Provide level 0-100 or get=true",
                    code=ErrorCode.BAD_ARGS,
                )
        level = int(params["level"])
        return self.adapter.set_volume(level)
