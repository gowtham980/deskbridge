# HANDOFF — DeskBridge v0.1

## What works
- Full Python package `deskbridge` with CLI + FastAPI web UI
- Darwin actions: status, screenshot, apps/urls, volume, notify, clipboard, lock, sleep-display
- Risk tiers + confirm gates
- SQLite audit log
- Dashboard / History / Settings UI
- pytest suite (domain, services, API, CLI)
- OpenClaw skill at `skill/desktop-control`
- Project image generator

## Run
```bash
cd open-source-solver-runs/deskbridge
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
deskbridge status
deskbridge serve
```

## Known gaps
- Lock may fall back to display-sleep without Accessibility
- No LAN auth yet (localhost default)
- No GUI click/OCR (intentional non-goal)
- Web UI is modern static/Jinja (not SPA) — intentional for install simplicity

## Parent notes
Builder subagent stalled mid-run; parent completed remaining docs/tests/image/skill packaging.
