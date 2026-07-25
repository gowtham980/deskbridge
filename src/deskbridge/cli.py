"""DeskBridge CLI entrypoint."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Sequence

from deskbridge import __version__
from deskbridge.paths import default_data_dir
from deskbridge.services.desktop import DesktopService


def _print_json(payload: dict[str, Any], exit_code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(exit_code)


def _service() -> DesktopService:
    return DesktopService(data_dir=default_data_dir())


def _run(
    action: str,
    params: dict[str, Any] | None = None,
    *,
    confirm: bool = False,
) -> None:
    svc = _service()
    result = svc.run_action(action, params or {}, source="cli", confirm=confirm)
    _print_json(result.to_dict(), exit_code=0 if result.ok else 1)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="deskbridge",
        description="DeskBridge — safe Mac desktop control for OpenClaw (CLI + local web).",
    )
    p.add_argument("--version", action="store_true", help="Print version JSON and exit")
    sub = p.add_subparsers(dest="command")

    serve = sub.add_parser("serve", help="Start local web console + API")
    serve.add_argument("--host", default=None, help="Bind host (default 127.0.0.1)")
    serve.add_argument("--port", type=int, default=None, help="Bind port (default 8788)")
    serve.add_argument("--reload", action="store_true", help="Dev auto-reload")

    sub.add_parser("status", help="Host + permission status")

    sp = sub.add_parser("screenshot", help="Capture screen")
    sp.add_argument("--display", choices=["main", "all"], default="main")
    sp.add_argument("--output", help="Output PNG path")

    sp = sub.add_parser("open-app", help="Open an application")
    sp.add_argument("name", help="App name or alias")

    sp = sub.add_parser("open-url", help="Open a URL")
    sp.add_argument("url")

    sub.add_parser("list-apps", help="List visible apps")

    sp = sub.add_parser("focus-app", help="Focus/activate an app")
    sp.add_argument("name")

    sp = sub.add_parser("quit-app", help="Quit an app (requires --yes)")
    sp.add_argument("name")
    sp.add_argument("--yes", action="store_true")

    sp = sub.add_parser("volume", help="Get/set output volume")
    sp.add_argument("--level", type=int, help="0-100")
    sp.add_argument("--get", action="store_true")

    sub.add_parser("mute")
    sub.add_parser("unmute")

    sp = sub.add_parser("notify", help="Display a macOS notification")
    sp.add_argument("--title", default="DeskBridge")
    sp.add_argument("--body", default="")
    sp.add_argument("--message", default="", help="Alias for --body")

    sp = sub.add_parser("sleep-display", help="Sleep displays (requires --yes)")
    sp.add_argument("--yes", action="store_true")

    sp = sub.add_parser("lock", help="Lock screen (requires --yes)")
    sp.add_argument("--yes", action="store_true")

    sub.add_parser("clipboard-get", help="Read clipboard text")
    sp = sub.add_parser("clipboard-set", help="Write clipboard text")
    sp.add_argument("text")

    sp = sub.add_parser("history", help="Show recent audited actions")
    sp.add_argument("--limit", type=int, default=20)

    return p


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    ns = parser.parse_args(list(argv) if argv is not None else None)

    if ns.version:
        _print_json({"ok": True, "action": "version", "version": __version__})

    if not ns.command:
        parser.print_help()
        raise SystemExit(2)

    if ns.command == "serve":
        from deskbridge.api.app import run_server

        svc = _service()
        settings = svc.config.load()
        host = ns.host or settings.bind_host or "127.0.0.1"
        port = int(ns.port or settings.bind_port or 8788)
        if ns.host or ns.port:
            svc.config.update(
                bind_host=host if ns.host else settings.bind_host,
                bind_port=port if ns.port else settings.bind_port,
            )
        run_server(host=host, port=port, reload=ns.reload, data_dir=svc.data_dir)
        return

    if ns.command == "status":
        _run("status")
    elif ns.command == "screenshot":
        params: dict[str, Any] = {"display": ns.display}
        if ns.output:
            params["output"] = ns.output
        _run("screenshot", params)
    elif ns.command == "open-app":
        _run("open-app", {"name": ns.name})
    elif ns.command == "open-url":
        _run("open-url", {"url": ns.url})
    elif ns.command == "list-apps":
        _run("list-apps")
    elif ns.command == "focus-app":
        _run("focus-app", {"name": ns.name})
    elif ns.command == "quit-app":
        _run("quit-app", {"name": ns.name, "yes": ns.yes}, confirm=bool(ns.yes))
    elif ns.command == "volume":
        params = {}
        if ns.get:
            params["get"] = True
        if ns.level is not None:
            params["level"] = ns.level
        if not params:
            params["get"] = True
        _run("volume", params)
    elif ns.command == "mute":
        _run("mute")
    elif ns.command == "unmute":
        _run("unmute")
    elif ns.command == "notify":
        body = ns.body or ns.message
        _run("notify", {"title": ns.title, "body": body})
    elif ns.command == "sleep-display":
        _run("sleep-display", {"yes": ns.yes}, confirm=bool(ns.yes))
    elif ns.command == "lock":
        _run("lock", {"yes": ns.yes}, confirm=bool(ns.yes))
    elif ns.command == "clipboard-get":
        _run("clipboard-get")
    elif ns.command == "clipboard-set":
        _run("clipboard-set", {"text": ns.text})
    elif ns.command == "history":
        _run("history", {"limit": ns.limit})
    else:
        parser.error(f"Unknown command: {ns.command}")


if __name__ == "__main__":
    main(sys.argv[1:])
