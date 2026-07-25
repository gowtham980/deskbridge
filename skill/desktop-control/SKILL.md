---
name: desktop-control
description: "Control a Mac desktop from OpenClaw via DeskBridge: screenshot, apps, volume, notify, lock, clipboard, and system status. Use for remote Mac control from ClawRemote or chat."
metadata:
  {
    "openclaw":
      {
        "emoji": "🖥️",
        "os": ["darwin"],
        "requires": { "bins": ["deskbridge"] }
      }
  }
---

# Desktop Control (DeskBridge)

Use the **DeskBridge** CLI on a macOS OpenClaw Gateway host.

## Install (once on gateway Mac)

```bash
pip install -e /path/to/deskbridge
# or: pipx install /path/to/deskbridge
```

If `deskbridge` is not on PATH, call via:

```bash
python3 -m deskbridge.cli <command>
```

## Commands

```bash
deskbridge status
deskbridge screenshot
deskbridge open-app "Safari"
deskbridge open-app chrome
deskbridge open-url https://example.com
deskbridge list-apps
deskbridge focus-app Slack
deskbridge quit-app Music --yes
deskbridge volume --get
deskbridge volume --level 30
deskbridge mute
deskbridge unmute
deskbridge notify --title "OpenClaw" --body "Done"
deskbridge lock --yes
deskbridge sleep-display --yes
deskbridge clipboard-get
deskbridge clipboard-set "text"
deskbridge history --limit 20
deskbridge serve   # local web UI http://127.0.0.1:8788
```

All action commands print JSON: `{ ok, action, risk, ... }`.

## Agent rules

1. Only on macOS gateway hosts.
2. On screenshot success, attach `path`/`media` with `MEDIA:<path>`.
3. `quit-app`, `lock`, `sleep-display` require explicit user intent + `--yes`.
4. Refuse shutdown/restart/mass-delete via this skill.
5. Surface JSON `hint` on permission failures (Screen Recording / Automation).

## Permissions

System Settings → Privacy & Security:
- Screen Recording (screenshots)
- Automation (list/quit apps)
- Accessibility (best-effort lock keystroke)
