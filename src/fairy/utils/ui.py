from __future__ import annotations

STATUS_EMOJI = {"pending": "⏳", "valid": "🟢", "warn": "🟡", "fail": "🔴"}

def status_chip(status: str | None) -> str:
    s = (status or "pending").lower()
    return f"{STATUS_EMOJI.get(s, '⏳')} {s}"

def format_bytes(n: int | None) -> str:
    if not n or n < 0: return "-"
    units = ["B","KB","MB","GB","TB"]
    i = 0
    x = float(n)
    while x >= 1024 and i < len(units)-1:
        x /= 1024.0; i += 1
    return f"{x:.1f}{units[i]}"

def shape_badge(rows: int | None, cols: int | None) -> str:
    r = rows if rows is not None else "?"
    c = cols if cols is not None else "?"
    return f"{r}×{c}"