# Contributing to DeskBridge

Thanks for helping improve DeskBridge.

## Dev setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Project layout

- `src/deskbridge/domain` — models, risk, errors
- `src/deskbridge/platform` — macOS adapter
- `src/deskbridge/services` — desktop + audit + config
- `src/deskbridge/api` + `web` — local console
- `tests/` — pytest
- `skill/` — OpenClaw skill shim

## Guidelines

1. Keep macOS built-ins only for MVP platform code (no companion app dependency).
2. Preserve risk tiers and confirm gates for high-risk actions.
3. Prefer JSON-stable CLI output for agents.
4. Default bind stays `127.0.0.1`.
5. Add/adjust tests with behavior changes.
6. Do not commit secrets, tokens, or personal screenshots.

## Pull requests

- Small focused PRs
- Describe user-facing impact
- Include test notes (`pytest` output summary)

## Release hygiene

- Bump version in `pyproject.toml` and `deskbridge/__init__.py`
- Update `ROADMAP.md` when shipping a milestone
