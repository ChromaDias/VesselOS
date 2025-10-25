from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple


Pair = Tuple[Path, dict]


def collect_pairs(vault: Path) -> List[Pair]:
    entries = vault / "entries"
    dreams = vault / "dreams"
    files = []
    files.extend(entries.glob("*.json"))
    if dreams.exists():
        files.extend(dreams.glob("*.json"))
    pairs: List[Pair] = []
    for p in files:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        pairs.append((p, data))
    return pairs


def match_target(target: str, p: Path, d: dict) -> bool:
    if target == "*":
        return True
    if p.name == target or p.stem == target:
        return True
    if str(d.get("title", "")) == target:
        return True
    tags = [str(t) for t in (d.get("tags") or [])]
    return target in tags

