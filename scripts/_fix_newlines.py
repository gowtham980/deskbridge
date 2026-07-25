#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for p in root.rglob("*.py"):
    if p.name.startswith("_fix"):
        continue
    text = p.read_text(encoding="utf-8")
    if "\\n" not in text:
        continue
    fixed = text.replace("self.extra = extra or {}\\n", "self.extra = extra or {}\n")
    fixed = fixed.replace("if m:\\n", "if m:\n")
    if fixed != text:
        p.write_text(fixed, encoding="utf-8")
        print("fixed", p)
    else:
        idx = text.find("\\n")
        print("unfixed", p, repr(text[max(0, idx - 40) : idx + 40]))
