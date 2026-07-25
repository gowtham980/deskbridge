"""CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_cli_help():
    proc = subprocess.run(
        [sys.executable, "-m", "deskbridge.cli", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**dict(**__import__("os").environ), "PYTHONPATH": str(ROOT / "src")},
    )
    assert proc.returncode == 0
    assert "screenshot" in proc.stdout


def test_cli_version():
    proc = subprocess.run(
        [sys.executable, "-m", "deskbridge.cli", "--version"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**dict(**__import__("os").environ), "PYTHONPATH": str(ROOT / "src")},
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["ok"] is True
    assert "version" in data
