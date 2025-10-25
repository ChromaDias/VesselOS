from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .store import collect_pairs, match_target
from .render import render_single, EXT_MAP
from .query import label_for
from .utils import sanitize


def run(target: str, fmt: str, with_metadata: bool, output: Optional[str], vault: Path) -> int:
    cfg = vault / "config.json"
    entries = vault / "entries"
    if not (cfg.exists() and entries.exists()):
        print("[ERR] Vault not found: expected config.json and entries/ in --vault path")
        return 2

    pairs = collect_pairs(vault)
    chosen = [(p, d) for p, d in pairs if match_target(target, p, d)]
    if not chosen:
        print(f"[ERR] No entries matched: {target}")
        return 1

    fmt_l = (fmt or "md").lower()
    ext = EXT_MAP.get(fmt_l, ".txt")
    exports = vault / "exports"
    exports.mkdir(parents=True, exist_ok=True)

    if len(chosen) == 1 and target != "*":
        p, d = chosen[0]
        if output:
            out_path = exports / output
        else:
            datep = str(d.get("anchor_date") or d.get("created_at") or "").split("T")[0] or "undated"
            label = label_for(d)
            fname = f"{label}__{sanitize(str(d.get('title') or p.stem))}__{sanitize(datep)}{ext}"
            out_path = exports / fname
        rendered = render_single(d, fmt_l, with_metadata)
        out_path.write_text(rendered, encoding="utf-8")
        if fmt_l in ("pdf", "rtf"):
            print(f"[OK] Wrote {fmt_l.upper()} content (markdown fallback) to {out_path}. Use pandoc for conversion if needed.")
        else:
            print(f"[OK] Exported to {out_path}")
        return 0

    # Bundle (multiple entries or wildcard)
    if fmt_l == "json":
        bundle = [d if with_metadata else {k: d.get(k) for k in ("title", "body") if d.get(k) is not None} for _, d in chosen]
        out_path = (exports / (output or (f"CodexExport__all{ext}" if target == "*" else f"CodexExport__{sanitize(target)}{ext}")))
        out_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
        print(f"[OK] Exported {len(chosen)} entries to {out_path}")
        return 0
    if fmt_l == "yaml":
        try:
            import yaml  # type: ignore
            bundle = [d if with_metadata else {k: d.get(k) for k in ("title", "body") if d.get(k) is not None} for _, d in chosen]
            out_path = (exports / (output or (f"CodexExport__all{ext}" if target == "*" else f"CodexExport__{sanitize(target)}{ext}")))
            out_path.write_text(yaml.safe_dump(bundle, sort_keys=False), encoding="utf-8")
            print(f"[OK] Exported {len(chosen)} entries to {out_path}")
            return 0
        except Exception:
            fmt_l = "md"  # fall through

    # md/txt/html/pdf/rtf bundle
    block_fmt = "md" if fmt_l in ("md", "pdf", "rtf") else ("txt" if fmt_l == "txt" else fmt_l)
    sep = "\n---\n\n"
    parts = [render_single(d, block_fmt, with_metadata) for _, d in chosen]
    out_path = (exports / (output or (f"CodexExport__all{ext}" if target == "*" else f"CodexExport__{sanitize(target)}{ext}")))
    out_path.write_text(sep.join(parts), encoding="utf-8")
    if fmt_l in ("pdf", "rtf"):
        print(f"[OK] Wrote {fmt_l.upper()} content (markdown fallback) to {out_path}. Use pandoc for conversion if needed.")
    else:
        print(f"[OK] Exported {len(chosen)} entries to {out_path}")
    return 0

