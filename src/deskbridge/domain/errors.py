"""Typed errors with machine codes and human hints."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    BAD_ARGS = "bad_args"
    UNSUPPORTED_OS = "unsupported_os"
    CONFIRMATION_REQUIRED = "confirmation_required"
    PROTECTED_APP = "protected_app"
    SCREEN_RECORDING_REQUIRED = "screen_recording_required"
    AUTOMATION_REQUIRED = "automation_required"
    OPEN_FAILED = "open_failed"
    FOCUS_FAILED = "focus_failed"
    QUIT_FAILED = "quit_failed"
    VOLUME_FAILED = "volume_failed"
    NOTIFY_FAILED = "notify_failed"
    SLEEP_FAILED = "sleep_failed"
    LOCK_FAILED = "lock_failed"
    CLIPBOARD_FAILED = "clipboard_failed"
    UNKNOWN_ACTION = "unknown_action"
    TIMEOUT = "timeout"
    INTERNAL_ERROR = "internal_error"
    NOT_FOUND = "not_found"
    SETTINGS_ERROR = "settings_error"


class DeskBridgeError(Exception):
    """Domain error with stable machine code + optional human hint."""

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode | str = ErrorCode.INTERNAL_ERROR,
        hint: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = str(code)
        self.hint = hint
        self.extra = extra or {}

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "error": self.message,
            "code": self.code,
        }
        if self.hint:
            payload["hint"] = self.hint
        if self.extra:
            payload.update(self.extra)
        return payload
