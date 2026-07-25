"""Darwin/macOS platform adapter using built-in tools only."""

from __future__ import annotations

import platform
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from deskbridge.domain.apps import normalize_url, parse_battery_output, resolve_app_name
from deskbridge.domain.errors import DeskBridgeError, ErrorCode
from deskbridge.domain.risk import PROTECTED_APPS


class DarwinAdapter:
    """Thin wrapper over macOS CLI tools (screencapture, open, osascript, pmset)."""

    def __init__(self, media_dir: Path) -> None:
        self.media_dir = media_dir
        self.media_dir.mkdir(parents=True, exist_ok=True)

    # --- process helpers -------------------------------------------------

    def is_darwin(self) -> bool:
        return platform.system() == "Darwin"

    def require_darwin(self) -> None:
        if not self.is_darwin():
            raise DeskBridgeError(
                f"DeskBridge requires macOS; host is {platform.system()}",
                code=ErrorCode.UNSUPPORTED_OS,
                hint="Run DeskBridge / OpenClaw Gateway on a Mac.",
            )

    def run(
        self,
        args: list[str],
        *,
        timeout: float = 30,
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            input=input_text,
            text=True,
            capture_output=True,
            timeout=timeout,
        )

    def run_osascript(self, script: str, *, timeout: float = 30) -> subprocess.CompletedProcess[str]:
        return self.run(["/usr/bin/osascript", "-e", script], timeout=timeout)

    @staticmethod
    def _esc_as(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')

    # --- status ----------------------------------------------------------

    def status(self) -> dict[str, Any]:
        self.require_darwin()
        info: dict[str, Any] = {
            "os": platform.system(),
            "platform": platform.platform(),
            "arch": platform.machine(),
            "hostname": platform.node(),
        }

        sw = self.run(["/usr/bin/sw_vers"], timeout=10)
        if sw.returncode == 0:
            for line in sw.stdout.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    info[k.strip().replace(" ", "_").lower()] = v.strip()

        batt = self.run(["/usr/bin/pmset", "-g", "batt"], timeout=10)
        if batt.returncode == 0:
            info.update(parse_battery_output(batt.stdout))

        disk = self.run(["/bin/df", "-h", "/"], timeout=10)
        if disk.returncode == 0:
            lines = disk.stdout.strip().splitlines()
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 5:
                    info["disk"] = {
                        "size": parts[1],
                        "used": parts[2],
                        "avail": parts[3],
                        "capacity": parts[4],
                        "mount": parts[-1],
                    }

        up = self.run(["/usr/bin/uptime"], timeout=10)
        if up.returncode == 0:
            info["uptime"] = up.stdout.strip()

        info["permissions"] = self.probe_permissions()
        return info

    def probe_permissions(self) -> dict[str, Any]:
        perms: dict[str, Any] = {}
        probe = self.media_dir / f"probe-{int(time.time())}.png"
        try:
            cap = self.run(["/usr/sbin/screencapture", "-x", "-t", "png", str(probe)], timeout=15)
            if cap.returncode == 0 and probe.exists() and probe.stat().st_size > 0:
                perms["screen_recording"] = "ok"
            else:
                perms["screen_recording"] = "missing_or_denied"
                perms["screen_recording_hint"] = (
                    "Grant Screen Recording to the process running DeskBridge / OpenClaw Gateway "
                    "(Terminal, iTerm, node, etc.) in System Settings → Privacy & Security → Screen Recording."
                )
        finally:
            try:
                probe.unlink(missing_ok=True)
            except OSError:
                pass

        osa = self.run_osascript('return "ok"')
        perms["osascript"] = "ok" if osa.returncode == 0 else "failed"
        return perms

    # --- screenshot ------------------------------------------------------

    def screenshot(self, *, display: str = "main", output: str | None = None) -> dict[str, Any]:
        self.require_darwin()
        ts = time.strftime("%Y%m%d-%H%M%S")
        path = Path(output) if output else self.media_dir / f"screenshot-{ts}.png"
        path.parent.mkdir(parents=True, exist_ok=True)

        args = ["/usr/sbin/screencapture", "-x", "-t", "png"]
        if display == "main":
            args.append("-m")
        args.append(str(path))

        proc = self.run(args, timeout=20)
        if proc.returncode != 0 or not path.exists() or path.stat().st_size == 0:
            raise DeskBridgeError(
                (proc.stderr or proc.stdout or "screencapture failed").strip()
                or "screencapture failed",
                code=ErrorCode.SCREEN_RECORDING_REQUIRED,
                hint=(
                    "Grant Screen Recording permission to the DeskBridge / OpenClaw Gateway host process "
                    "(Terminal/iTerm/node) in System Settings → Privacy & Security → Screen Recording, "
                    "then restart the process."
                ),
                extra={"path": str(path)},
            )

        return {
            "path": str(path),
            "media": str(path),
            "bytes": path.stat().st_size,
            "display": display,
            "filename": path.name,
        }

    # --- apps / urls -----------------------------------------------------

    def open_app(self, name: str) -> dict[str, Any]:
        self.require_darwin()
        app = resolve_app_name(name)
        if not app:
            raise DeskBridgeError("App name required", code=ErrorCode.BAD_ARGS)
        proc = self.run(["/usr/bin/open", "-a", app], timeout=20)
        if proc.returncode != 0:
            raise DeskBridgeError(
                (proc.stderr or proc.stdout or f"Failed to open {app}").strip(),
                code=ErrorCode.OPEN_FAILED,
                hint="Pass the exact app name as shown in /Applications.",
                extra={"app": app},
            )
        return {"app": app}

    def open_url(self, url: str) -> dict[str, Any]:
        self.require_darwin()
        normalized = normalize_url(url)
        if not normalized:
            raise DeskBridgeError("URL required", code=ErrorCode.BAD_ARGS)
        proc = self.run(["/usr/bin/open", normalized], timeout=20)
        if proc.returncode != 0:
            raise DeskBridgeError(
                (proc.stderr or "open failed").strip(),
                code=ErrorCode.OPEN_FAILED,
                extra={"url": normalized},
            )
        return {"url": normalized}

    def list_apps(self) -> dict[str, Any]:
        self.require_darwin()
        script = """
        tell application "System Events"
          set procs to (name of every process whose background only is false)
        end tell
        set AppleScript's text item delimiters to linefeed
        return procs as text
        """
        proc = self.run_osascript(script)
        if proc.returncode != 0:
            raise DeskBridgeError(
                (proc.stderr or "osascript failed").strip(),
                code=ErrorCode.AUTOMATION_REQUIRED,
                hint="Grant Automation permission for System Events to the host process.",
            )
        apps = sorted({line.strip() for line in proc.stdout.splitlines() if line.strip()})
        return {"apps": apps, "count": len(apps)}

    def focus_app(self, name: str) -> dict[str, Any]:
        self.require_darwin()
        app = resolve_app_name(name)
        if not app:
            raise DeskBridgeError("App name required", code=ErrorCode.BAD_ARGS)
        script = f'tell application "{self._esc_as(app)}" to activate'
        proc = self.run_osascript(script)
        if proc.returncode != 0:
            proc2 = self.run(["/usr/bin/open", "-a", app], timeout=20)
            if proc2.returncode != 0:
                raise DeskBridgeError(
                    (proc.stderr or proc2.stderr or f"Failed to focus {app}").strip(),
                    code=ErrorCode.FOCUS_FAILED,
                    extra={"app": app},
                )
        return {"app": app}

    def quit_app(self, name: str, *, confirm: bool) -> dict[str, Any]:
        self.require_darwin()
        app = resolve_app_name(name)
        if not app:
            raise DeskBridgeError("App name required", code=ErrorCode.BAD_ARGS)
        if app.lower() in PROTECTED_APPS:
            raise DeskBridgeError(
                f"Refusing to quit protected app: {app}",
                code=ErrorCode.PROTECTED_APP,
                extra={"app": app},
            )
        if not confirm:
            raise DeskBridgeError(
                f"Refusing to quit '{app}' without confirmation",
                code=ErrorCode.CONFIRMATION_REQUIRED,
                hint="Pass --yes (CLI) or confirm=true (API) after user confirmation.",
                extra={"app": app},
            )
        script = f'tell application "{self._esc_as(app)}" to quit'
        proc = self.run_osascript(script)
        if proc.returncode != 0:
            raise DeskBridgeError(
                (proc.stderr or f"Failed to quit {app}").strip(),
                code=ErrorCode.QUIT_FAILED,
                hint="App may need Accessibility/Automation permission, or name may be wrong.",
                extra={"app": app},
            )
        return {"app": app}

    # --- volume ----------------------------------------------------------

    def get_volume(self) -> dict[str, Any]:
        self.require_darwin()
        proc = self.run_osascript("get volume settings")
        if proc.returncode != 0:
            raise DeskBridgeError(
                (proc.stderr or "failed to read volume").strip(),
                code=ErrorCode.VOLUME_FAILED,
            )
        text = proc.stdout.strip()
        result: dict[str, Any] = {"raw": text}
        m = re.search(r"output volume:(\d+)", text)
        if m:
            result["output_volume"] = int(m.group(1))
        m = re.search(r"output muted:(true|false)", text)
        if m:
            result["muted"] = m.group(1) == "true"
        return result

    def set_volume(self, level: int) -> dict[str, Any]:
        self.require_darwin()
        if level < 0 or level > 100:
            raise DeskBridgeError("Volume level must be 0-100", code=ErrorCode.BAD_ARGS)
        proc = self.run_osascript(f"set volume output volume {level}")
        if proc.returncode != 0:
            raise DeskBridgeError(
                (proc.stderr or "failed to set volume").strip(),
                code=ErrorCode.VOLUME_FAILED,
            )
        self.run_osascript("set volume output muted false")
        try:
            current = self.get_volume()
        except DeskBridgeError:
            current = {"output_volume": level}
        return {"level": level, "result": current}

    def mute(self) -> dict[str, Any]:
        self.require_darwin()
        proc = self.run_osascript("set volume output muted true")
        if proc.returncode != 0:
            raise DeskBridgeError(
                (proc.stderr or "mute failed").strip(),
                code=ErrorCode.VOLUME_FAILED,
            )
        return {"muted": True}

    def unmute(self) -> dict[str, Any]:
        self.require_darwin()
        proc = self.run_osascript("set volume output muted false")
        if proc.returncode != 0:
            raise DeskBridgeError(
                (proc.stderr or "unmute failed").strip(),
                code=ErrorCode.VOLUME_FAILED,
            )
        return {"muted": False}

    # --- notify ----------------------------------------------------------

    def notify(self, *, title: str, body: str) -> dict[str, Any]:
        self.require_darwin()
        if not body:
            raise DeskBridgeError("Notification body required", code=ErrorCode.BAD_ARGS)
        title = title or "DeskBridge"
        script = (
            f'display notification "{self._esc_as(body)}" '
            f'with title "{self._esc_as(title)}"'
        )
        proc = self.run_osascript(script)
        if proc.returncode != 0:
            raise DeskBridgeError(
                (proc.stderr or "notification failed").strip(),
                code=ErrorCode.NOTIFY_FAILED,
                hint="macOS may require notification permission for osascript context.",
            )
        return {"title": title, "body": body}

    # --- session ---------------------------------------------------------

    def sleep_display(self, *, confirm: bool) -> dict[str, Any]:
        self.require_darwin()
        if not confirm:
            raise DeskBridgeError(
                "Refusing to sleep display without confirmation",
                code=ErrorCode.CONFIRMATION_REQUIRED,
                hint="Pass --yes (CLI) or confirm=true (API) after explicit user request.",
            )
        proc = self.run(["/usr/bin/pmset", "displaysleepnow"], timeout=15)
        if proc.returncode != 0:
            raise DeskBridgeError(
                (proc.stderr or "pmset failed").strip(),
                code=ErrorCode.SLEEP_FAILED,
            )
        return {"message": "Display sleep requested"}

    def lock(self, *, confirm: bool) -> dict[str, Any]:
        self.require_darwin()
        if not confirm:
            raise DeskBridgeError(
                "Refusing to lock screen without confirmation",
                code=ErrorCode.CONFIRMATION_REQUIRED,
                hint="Pass --yes (CLI) or confirm=true (API) after explicit user request.",
            )

        attempts: list[dict[str, Any]] = []

        cgs = Path(
            "/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession"
        )
        if cgs.exists():
            proc = self.run([str(cgs), "-suspend"], timeout=15)
            attempts.append(
                {
                    "method": "CGSession",
                    "returncode": proc.returncode,
                    "stderr": (proc.stderr or "").strip(),
                }
            )
            if proc.returncode == 0:
                return {
                    "method": "CGSession",
                    "message": "Screen lock requested",
                    "attempts": attempts,
                }

        script = (
            'tell application "System Events" to keystroke "q" '
            "using {control down, command down}"
        )
        proc = self.run_osascript(script)
        attempts.append(
            {
                "method": "ctrl+cmd+q",
                "returncode": proc.returncode,
                "stderr": (proc.stderr or "").strip(),
            }
        )
        if proc.returncode == 0:
            return {
                "method": "ctrl+cmd+q",
                "message": "Screen lock keystroke sent (requires Accessibility)",
                "attempts": attempts,
            }

        proc = self.run(["/usr/bin/pmset", "displaysleepnow"], timeout=15)
        attempts.append(
            {
                "method": "pmset_displaysleepnow",
                "returncode": proc.returncode,
                "stderr": (proc.stderr or "").strip(),
            }
        )
        if proc.returncode == 0:
            return {
                "method": "pmset_displaysleepnow",
                "message": "Could not hard-lock; display sleep requested instead",
                "warning": "Full lock may require Accessibility permission for keystroke lock.",
                "attempts": attempts,
            }

        raise DeskBridgeError(
            "All lock methods failed",
            code=ErrorCode.LOCK_FAILED,
            hint=(
                "Grant Accessibility to the host process for Ctrl+Cmd+Q lock, "
                "or use a Mac login password policy with CGSession."
            ),
            extra={"attempts": attempts},
        )

    # --- clipboard -------------------------------------------------------

    def clipboard_get(self) -> dict[str, Any]:
        self.require_darwin()
        proc = self.run(["/usr/bin/pbpaste"], timeout=10)
        if proc.returncode != 0:
            raise DeskBridgeError(
                (proc.stderr or "pbpaste failed").strip(),
                code=ErrorCode.CLIPBOARD_FAILED,
            )
        text = proc.stdout
        truncated = False
        if len(text) > 20_000:
            text = text[:20_000]
            truncated = True
        return {"text": text, "truncated": truncated, "length": len(proc.stdout)}

    def clipboard_set(self, text: str) -> dict[str, Any]:
        self.require_darwin()
        if text is None:
            raise DeskBridgeError("Text required", code=ErrorCode.BAD_ARGS)
        proc = self.run(["/usr/bin/pbcopy"], timeout=10, input_text=text)
        if proc.returncode != 0:
            raise DeskBridgeError(
                (proc.stderr or "pbcopy failed").strip(),
                code=ErrorCode.CLIPBOARD_FAILED,
            )
        return {"length": len(text)}
