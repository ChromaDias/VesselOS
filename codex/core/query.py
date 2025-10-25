from __future__ import annotations

from pathlib import Path
from typing import List, Tuple


Pair = Tuple[Path, dict]


def is_dream(d: dict) -> bool:
    tags = [str(t).lower() for t in (d.get("tags") or [])]
    if any(t in tags for t in ("dream", "dreams", "oneiric", "sleep", "vision")):
        return True
    meta = d.get("metadata") or {}
    if str(meta.get("origin", "")).lower() == "dream":
        return True
    for k in ("category", "type", "state"):
        v = str(meta.get(k, "")).lower()
        if "dream" in v or "oneiric" in v:
            return True
    return False


def label_for(d: dict) -> str:
    return "DreamEntry" if is_dream(d) else "Entry"

