"""App name aliases and helpers."""

from __future__ import annotations

import re

# Common short names → macOS app names
APP_ALIASES: dict[str, str] = {
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "safari": "Safari",
    "firefox": "Firefox",
    "edge": "Microsoft Edge",
    "code": "Visual Studio Code",
    "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "cursor": "Cursor",
    "terminal": "Terminal",
    "iterm": "iTerm",
    "iterm2": "iTerm",
    "finder": "Finder",
    "notes": "Notes",
    "mail": "Mail",
    "messages": "Messages",
    "slack": "Slack",
    "discord": "Discord",
    "spotify": "Spotify",
    "music": "Music",
    "notion": "Notion",
    "figma": "Figma",
    "zoom": "zoom.us",
    "telegram": "Telegram",
    "whatsapp": "WhatsApp",
    "preview": "Preview",
    "xcode": "Xcode",
    "system settings": "System Settings",
    "settings": "System Settings",
    "activity monitor": "Activity Monitor",
    "obsidian": "Obsidian",
    "arc": "Arc",
    "brave": "Brave Browser",
}


def resolve_app_name(name: str) -> str:
    cleaned = " ".join(name.strip().split())
    if not cleaned:
        return cleaned
    alias = APP_ALIASES.get(cleaned.lower())
    return alias or cleaned


def normalize_url(url: str) -> str:
    cleaned = url.strip()
    if not cleaned:
        return cleaned
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", cleaned):
        return "https://" + cleaned
    return cleaned


def parse_battery_output(raw: str) -> dict[str, object]:
    """Parse `pmset -g batt` output into structured fields."""
    info: dict[str, object] = {"battery_raw": raw.strip()}
    m = re.search(r"(\d+)%", raw)
    if m:
        info["battery_percent"] = int(m.group(1))
    raw_l = raw.lower()
    info["battery_charging"] = (
        "ac power" in raw_l or ("charging" in raw_l and "discharging" not in raw_l)
    )
    info["on_ac"] = "ac power" in raw_l
    return info
