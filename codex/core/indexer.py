from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from .store import collect_pairs
from .query import is_dream


def build_index(vault: Path) -> Path:
    system = vault / "system"
    system.mkdir(parents=True, exist_ok=True)
    index_path = system / "index.json"
    items: List[Dict] = []
    for p, d in collect_pairs(vault):
        items.append(
            {
                "file": str(p.name),
                "path": str(p.relative_to(vault)),
                "title": d.get("title"),
                "tags": d.get("tags") or [],
                "type": ("dream" if is_dream(d) else (d.get("metadata", {}) or {}).get("type", "entry")),
                "created_at": d.get("created_at"),
                "anchor_date": d.get("anchor_date"),
            }
        )
    index_path.write_text(json.dumps({"items": items}, indent=2), encoding="utf-8")
    return index_path


def list_entries(vault: Path, tag: str | None = None, date: str | None = None, typ: str | None = None) -> List[Tuple[str, Dict]]:
    index_path = vault / "system" / "index.json"
    if not index_path.exists():
        build_index(vault)
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
        items = data.get("items", [])
    except Exception:
        items = []
    out = []
    for it in items:
        if tag and tag not in (it.get("tags") or []):
            continue
        if date:
            c = str(it.get("created_at") or "")
            a = str(it.get("anchor_date") or "")
            if not (c.startswith(date) or a.startswith(date)):
                continue
        if typ and str(it.get("type") or "").lower() != typ.lower():
            continue
        out.append((it.get("file"), it))
    return out

