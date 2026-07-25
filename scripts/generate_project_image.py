#!/usr/bin/env python3
"""Generate docs/images/project.png hero image for DeskBridge."""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path


def _png(width: int, height: int, rgb_pixels: list[tuple[int, int, int]]) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            r, g, b = rgb_pixels[y * width + x]
            raw.extend((r, g, b))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            chunk(b"IHDR", ihdr),
            chunk(b"IDAT", zlib.compress(bytes(raw), 9)),
            chunk(b"IEND", b""),
        ]
    )


def _blend(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


def _glyph(ch: str) -> list[str]:
    # Minimal 5x7 glyphs for the word DESKBRIDGE / tagline bits
    font = {
        "D": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
        "E": ["11111", "10000", "11110", "10000", "10000", "10000", "11111"],
        "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
        "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
        "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
        "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
        "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
        "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01110"],
        " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
        "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
        "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
        "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
        "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
        "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
        "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
        "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
        "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
        "M": ["10001", "11011", "10101", "10001", "10001", "10001", "10001"],
        "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
        "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
        "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
        "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
        "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
        "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
        "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
        "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
        ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
        "/": ["00001", "00010", "00100", "01000", "10000", "10000", "10000"],
        "+": ["00000", "00100", "00100", "11111", "00100", "00100", "00000"],
        ":": ["00000", "01100", "01100", "00000", "01100", "01100", "00000"],
    }
    return font.get(ch.upper(), font[" "])


def _draw_text(
    pixels: list[tuple[int, int, int]],
    width: int,
    text: str,
    x0: int,
    y0: int,
    scale: int,
    color: tuple[int, int, int],
) -> None:
    cx = x0
    for ch in text:
        glyph = _glyph(ch)
        for gy, row in enumerate(glyph):
            for gx, bit in enumerate(row):
                if bit == "1":
                    for sy in range(scale):
                        for sx in range(scale):
                            x = cx + gx * scale + sx
                            y = y0 + gy * scale + sy
                            if 0 <= x < width and 0 <= y < len(pixels) // width:
                                pixels[y * width + x] = color
        cx += 6 * scale


def generate(path: Path) -> None:
    width, height = 1280, 720
    c1 = (10, 14, 28)
    c2 = (18, 28, 52)
    accent = (0, 229, 255)
    accent2 = (167, 139, 250)
    white = (230, 240, 255)
    muted = (148, 163, 184)

    pixels: list[tuple[int, int, int]] = []
    for y in range(height):
        for x in range(width):
            t = y / height
            wave = 0.08 * math.sin(x / 70 + y / 90)
            base = _blend(c1, c2, min(1.0, max(0.0, t + wave)))
            # soft vignette corner glow
            dx = (x - width * 0.75) / width
            dy = (y - height * 0.3) / height
            glow = max(0.0, 1.0 - math.sqrt(dx * dx + dy * dy) * 2.2)
            gcol = _blend(base, accent2, glow * 0.25)
            # grid
            if x % 48 == 0 or y % 48 == 0:
                gcol = _blend(gcol, (30, 41, 59), 0.25)
            pixels.append(gcol)

    # panel card
    def fill_rect(x1, y1, x2, y2, color, alpha=1.0):
        for y in range(y1, y2):
            for x in range(x1, x2):
                if 0 <= x < width and 0 <= y < height:
                    i = y * width + x
                    pixels[i] = _blend(pixels[i], color, alpha)

    fill_rect(80, 90, 620, 630, (15, 23, 42), 0.82)
    fill_rect(660, 120, 1200, 600, (15, 23, 42), 0.75)

    _draw_text(pixels, width, "DESKBRIDGE", 110, 130, 5, accent)
    _draw_text(pixels, width, "SAFE MAC DESKTOP CONTROL", 110, 200, 2, white)
    _draw_text(pixels, width, "FOR OPENCLAW AGENTS", 110, 230, 2, muted)
    _draw_text(pixels, width, "CLI + LOCAL WEB + SKILL", 110, 300, 2, accent2)
    _draw_text(pixels, width, "SCREENSHOT  APPS  VOLUME", 110, 360, 2, white)
    _draw_text(pixels, width, "LOCK  AUDIT  JSON API", 110, 400, 2, white)
    _draw_text(pixels, width, "NO MACOS COMPANION APP", 110, 470, 2, muted)
    _draw_text(pixels, width, "GATEWAY + PHONE READY", 110, 510, 2, muted)

    # fake UI chrome on right
    _draw_text(pixels, width, "DASHBOARD", 700, 150, 3, white)
    _draw_text(pixels, width, "BATTERY  96%", 700, 220, 2, accent)
    _draw_text(pixels, width, "DISK     94GI FREE", 700, 260, 2, accent)
    _draw_text(pixels, width, "SCREEN   OK", 700, 300, 2, accent)
    fill_rect(700, 360, 1140, 560, (2, 6, 23), 0.9)
    _draw_text(pixels, width, "LATEST SCREENSHOT", 720, 390, 2, muted)
    _draw_text(pixels, width, "[ PREVIEW ]", 820, 460, 3, accent2)
    _draw_text(pixels, width, "v0.1  MIT  LOCAL-FIRST", 700, 580, 2, muted)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_png(width, height, pixels))
    print(f"wrote {path}")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    generate(root / "docs" / "images" / "project.png")
