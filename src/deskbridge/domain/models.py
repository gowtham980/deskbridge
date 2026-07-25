"""Domain models for DeskBridge."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from deskbridge.domain.risk import RiskLevel


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class ActionResult:
    ok: bool
    action: str
    risk: RiskLevel | str
    version: str
    message: str | None = None
    error: str | None = None
    code: str | None = None
    hint: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ok": self.ok,
            "action": self.action,
            "risk": str(self.risk),
            "version": self.version,
        }
        if self.message is not None:
            payload["message"] = self.message
        if self.error is not None:
            payload["error"] = self.error
        if self.code is not None:
            payload["code"] = self.code
        if self.hint is not None:
            payload["hint"] = self.hint
        # Flatten data keys at top-level for agent-friendly JSON
        for key, value in self.data.items():
            if key not in payload:
                payload[key] = value
        return payload


@dataclass
class ActionRecord:
    id: int | None
    ts: str
    action: str
    params_json: str
    risk: str
    ok: bool
    result_json: str
    error: str | None
    source: str  # cli | web | api

    @classmethod
    def create(
        cls,
        *,
        action: str,
        params: dict[str, Any],
        risk: str,
        ok: bool,
        result: dict[str, Any],
        error: str | None,
        source: str,
        ts: str | None = None,
        record_id: int | None = None,
    ) -> ActionRecord:
        return cls(
            id=record_id,
            ts=ts or utc_now_iso(),
            action=action,
            params_json=json.dumps(params, ensure_ascii=False, default=str),
            risk=risk,
            ok=ok,
            result_json=json.dumps(result, ensure_ascii=False, default=str),
            error=error,
            source=source,
        )

    def to_dict(self) -> dict[str, Any]:
        try:
            params = json.loads(self.params_json) if self.params_json else {}
        except json.JSONDecodeError:
            params = {"raw": self.params_json}
        try:
            result = json.loads(self.result_json) if self.result_json else {}
        except json.JSONDecodeError:
            result = {"raw": self.result_json}
        return {
            "id": self.id,
            "ts": self.ts,
            "action": self.action,
            "params": params,
            "risk": self.risk,
            "ok": self.ok,
            "result": result,
            "error": self.error,
            "source": self.source,
        }


@dataclass
class Settings:
    bind_host: str = "127.0.0.1"
    bind_port: int = 8788
    allow_high_risk: bool = True
    media_retention: int = 50  # keep last N screenshots
    data_dir: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Settings:
        if not data:
            return cls()
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)
