"""Risk tiers and confirmation policy for desktop actions."""

from __future__ import annotations

from enum import StrEnum


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


RISK: dict[str, RiskLevel] = {
    "status": RiskLevel.LOW,
    "screenshot": RiskLevel.LOW,
    "open-app": RiskLevel.LOW,
    "open-url": RiskLevel.LOW,
    "list-apps": RiskLevel.LOW,
    "volume": RiskLevel.LOW,
    "mute": RiskLevel.LOW,
    "unmute": RiskLevel.LOW,
    "notify": RiskLevel.LOW,
    "focus-app": RiskLevel.MEDIUM,
    "quit-app": RiskLevel.MEDIUM,
    "clipboard-get": RiskLevel.MEDIUM,
    "clipboard-set": RiskLevel.MEDIUM,
    "sleep-display": RiskLevel.HIGH,
    "lock": RiskLevel.HIGH,
    "history": RiskLevel.LOW,
}

# Actions that require an explicit confirm / --yes flag
CONFIRM_REQUIRED: frozenset[str] = frozenset(
    {
        "quit-app",
        "lock",
        "sleep-display",
    }
)

PROTECTED_APPS: frozenset[str] = frozenset(
    {
        "finder",
        "loginwindow",
        "dock",
        "systemui server",
        "windowserver",
        "systemui server",
    }
)


def risk_for(action: str) -> RiskLevel:
    return RISK.get(action, RiskLevel.UNKNOWN)


def requires_confirm(action: str) -> bool:
    return action in CONFIRM_REQUIRED
