from __future__ import annotations


def sanitize(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in (name or "")).strip("._") or "entry"

