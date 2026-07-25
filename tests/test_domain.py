"""Domain unit tests."""

from __future__ import annotations

from deskbridge.domain.apps import normalize_url, parse_battery_output, resolve_app_name
from deskbridge.domain.risk import RISK, requires_confirm, risk_for


def test_resolve_app_aliases():
    assert resolve_app_name("chrome") == "Google Chrome"
    assert resolve_app_name("Safari") == "Safari"
    assert resolve_app_name("  vs code ") == "Visual Studio Code"


def test_normalize_url():
    assert normalize_url("example.com") == "https://example.com"
    assert normalize_url("https://x.test") == "https://x.test"
    assert normalize_url("http://x.test") == "http://x.test"


def test_parse_battery_discharging_not_charging():
    raw = "Now drawing from 'Battery Power'\n -InternalBattery-0\t96%; discharging; 6:47 remaining present: true"
    info = parse_battery_output(raw)
    assert info["battery_percent"] == 96
    assert info["battery_charging"] is False
    assert info["on_ac"] is False


def test_parse_battery_ac():
    raw = "Now drawing from 'AC Power'\n -InternalBattery-0\t80%; charged; present: true"
    info = parse_battery_output(raw)
    assert info["on_ac"] is True
    assert info["battery_percent"] == 80


def test_risk_policy():
    assert str(risk_for("screenshot")) == "low"
    assert str(risk_for("quit-app")) == "medium"
    assert str(risk_for("lock")) == "high"
    assert requires_confirm("lock") is True
    assert requires_confirm("screenshot") is False
    assert "history" in RISK
