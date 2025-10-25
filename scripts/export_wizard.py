#!/usr/bin/env python3
"""
Codex Export Wizard – interactive helper to export entries from a vault.

Guides through:
1) What to export (single entry, tag group, folder, search, all)
2) Output format (md/txt/json/yaml/pdf/html/rtf)
3) Metadata include (yes/no)
4) Output naming and location (exports/, codex/archive, custom)
5) Confirmation and execution (single file or per-entry split)

This script is self-contained and does not require Click; it reads from stdin.
It writes files directly (not via the codex CLI) to support flexible destinations.
"""

from __future__ import annotations

import json
import sys
import re
from pathlib import Path
from datetime import datetime

try:
    import yaml  # type: ignore
except Exception:  # optional
    yaml = None  # type: ignore


def _sanitize(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in (name or "")).strip("._") or "entry"


def _prompt(q: str, valid: set[str] | None = None, default: str | None = None) -> str:
    while True:
        sfx = f" [{default}]" if default else ""
        val = input(f"{q}{sfx}: ").strip()
        if not val and default is not None:
            val = default
        if valid is None or val in valid:
            return val
        print(f"Please enter one of: {sorted(valid)}")


def _load_pairs(vault: Path) -> list[tuple[Path, dict]]:
    entries = vault / "entries"
    dreams = vault / "dreams"
    if not (vault / "config.json").exists() or not entries.exists():
        print("[ERR] Vault not found: expected config.json and entries/ in vault path", file=sys.stderr)
        sys.exit(2)
    files = list(entries.glob("*.json"))
    if dreams.exists():
        files += list(dreams.glob("*.json"))
    pairs: list[tuple[Path, dict]] = []
    for p in files:
        try:
            pairs.append((p, json.loads(p.read_text(encoding="utf-8"))))
        except Exception:
            continue
    return pairs


def _select_scope(vault: Path) -> tuple[str, list[tuple[Path, dict]]]:
    pairs = _load_pairs(vault)
    print(
        """
Select what to export:
  [1] Single entry (by title/file)
  [2] Tag group (e.g., harm_report, dream_log)
  [3] Folder (entries or dreams)
  [4] Search query (phrase in title/body)
  [5] Everything (full vault)
""".strip()
    )
    choice = _prompt("Choice", {"1", "2", "3", "4", "5"}, "1")
    if choice == "1":
        key = _prompt("Enter title or file name (stem)")
        sel = []
        for p, d in pairs:
            if p.name == key or p.stem == key or str(d.get("title", "")) == key:
                sel.append((p, d))
        if not sel:
            print("[ERR] No matching entry.")
            sys.exit(1)
        return ("single", sel)
    if choice == "2":
        tag = _prompt("Enter tag (symbolic key)")
        sel = []
        for p, d in pairs:
            tags = [str(t) for t in (d.get("tags") or [])]
            if tag in tags:
                sel.append((p, d))
        if not sel:
            print("[ERR] No entries with that tag.")
            sys.exit(1)
        return (f"tag:{tag}", sel)
    if choice == "3":
        folder = _prompt("Folder name", {"entries", "dreams"}, "entries")
        base = vault / folder
        sel = []
        for p, d in pairs:
            if p.parent == base:
                sel.append((p, d))
        return (f"folder:{folder}", sel)
    if choice == "4":
        phrase = _prompt("Enter search phrase")
        low = phrase.lower()
        sel = []
        for p, d in pairs:
            text = (str(d.get("title", "")) + "\n" + str(d.get("body", ""))).lower()
            if low in text:
                sel.append((p, d))
        if not sel:
            print("[ERR] No entries matched the phrase.")
            sys.exit(1)
        return (f"search:{phrase}", sel)
    # 5 – everything
    return ("all", pairs)


def _choose_format() -> str:
    print(
        """
Choose output format:
  [1] md   [2] txt   [3] json   [4] yaml   [5] pdf   [6] html   [7] rtf
""".strip()
    )
    choice = _prompt("Choice", {"1", "2", "3", "4", "5", "6", "7"}, "1")
    return {"1": "md", "2": "txt", "3": "json", "4": "yaml", "5": "pdf", "6": "html", "7": "rtf"}[choice]


def _render_single(d: dict, fmt: str, with_meta: bool) -> str:
    fmt = (fmt or "md").lower()
    if fmt == "json":
        obj = d if with_meta else {k: d.get(k) for k in ("title", "body") if d.get(k) is not None}
        return json.dumps(obj, indent=2)
    if fmt == "yaml":
        obj = d if with_meta else {k: d.get(k) for k in ("title", "body") if d.get(k) is not None}
        if yaml is None:
            return json.dumps(obj, indent=2)
        return yaml.safe_dump(obj, sort_keys=False)
    if fmt == "html":
        import html as _html
        title = _html.escape(str(d.get("title", "Untitled")))
        body = _html.escape(str(d.get("body", "") or "")).replace("\n", "<br/>")
        meta_block = ""
        if with_meta:
            created = _html.escape(str(d.get("created_at", "")))
            tags = ", ".join(_html.escape(str(x)) for x in (d.get("tags", []) or []))
            meta = _html.escape(json.dumps(d.get("metadata", {}) or {}, indent=2))
            meta_block = f"<p><em>Created:</em> {created} | <em>Tags:</em> {tags}</p><pre>{meta}</pre>"
        return f"<html><head><meta charset='utf-8'><title>{title}</title></head><body><h1>{title}</h1>{meta_block}<p>{body}</p></body></html>\n"
    # md/txt/pdf/rtf fallbacks
    title = d.get("title", "Untitled")
    body = d.get("body", "") or ""
    if fmt == "txt":
        return f"Title: {title}\n\n{body}\n"
    lines = [f"# {title}", ""]
    if with_meta:
        created = d.get("created_at", "")
        tags = d.get("tags", []) or []
        if created or tags:
            lines.append(f"- Created: {created}\n- Tags: {', '.join(tags)}\n")
    lines.append(body)
    if with_meta:
        meta = d.get("metadata", {}) or {}
        if meta:
            lines += ["", "## Metadata", "```json", json.dumps(meta, indent=2), "```"]
    return "\n".join(lines).rstrip() + "\n"


def _maybe_redact(text: str, patterns: list[str]) -> str:
    for pat in patterns:
        try:
            text = re.sub(pat, "[REDACTED]", text, flags=re.MULTILINE | re.DOTALL)
        except re.error:
            continue
    return text


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    # Vault path
    default_vault = Path.cwd()
    # Prefer an existing wizard-created vault if present under VesselOS/codex
    candidate = Path("VesselOS/codex/vessel_relics")
    if candidate.exists():
        default_vault = candidate
    vault_input = _prompt("Vault path", default=str(default_vault))
    vault = Path(vault_input).expanduser().resolve()

    scope_label, selected = _select_scope(vault)
    fmt = _choose_format()

    md_choice = _prompt("Include metadata? (y/n)", valid={"y", "n"}, default="y")
    with_meta = md_choice.lower().startswith("y")

    # Optional basic redaction
    do_redact = _prompt("Add redaction rules? (y/n)", valid={"y", "n"}, default="n")
    redact_patterns: list[str] = []
    if do_redact == "y":
        print("Enter regex to redact (one per line). Blank line to finish.")
        while True:
            pat = input("pattern> ").strip()
            if not pat:
                break
            redact_patterns.append(pat)

    # Split or bundle
    split_choice = _prompt("Split into one file per entry? (y/n)", valid={"y", "n"}, default="n")
    split = split_choice == "y"

    # Destination
    today = datetime.utcnow().strftime("%Y-%m-%d")
    base_name = (
        f"Codex_Export_{_sanitize(scope_label)}_{today}"
        if scope_label not in ("single", "all")
        else (
            f"Codex_Export_all_{today}" if scope_label == "all" else f"Codex_Export_{_sanitize(selected[0][1].get('title') or selected[0][0].stem)}_{today}"
        )
    )
    default_out = base_name + {
        "md": ".md",
        "txt": ".txt",
        "json": ".json",
        "yaml": ".yaml",
        "pdf": ".pdf",
        "html": ".html",
        "rtf": ".rtf",
    }[fmt]
    out_name = _prompt("Output filename", default=default_out)

    print(
        """
Save location:
  [1] exports/ (inside the vault)
  [2] codex/archive/ (inside the vault)
  [3] Custom directory (absolute or relative)
""".strip()
    )
    dest_choice = _prompt("Choice", {"1", "2", "3"}, "1")
    if dest_choice == "1":
        dest_dir = vault / "exports"
    elif dest_choice == "2":
        dest_dir = vault / "codex" / "archive"
    else:
        custom = _prompt("Enter destination directory path", default=str((vault / "exports")))
        dest_dir = Path(custom).expanduser().resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Summary
    print("\nSummary:")
    print(f"• Entries: {len(selected)}")
    print(f"• Format: {fmt}")
    print(f"• Metadata: {'included' if with_meta else 'stripped'}")
    print(f"• Split: {'yes' if split else 'no (bundle)'}")
    print(f"• Output: {dest_dir / out_name}")
    proceed = _prompt("Proceed? (y/n)", {"y", "n"}, "y")
    if proceed != "y":
        print("Cancelled.")
        return 0

    # Render and write
    ext = Path(out_name).suffix.lower()
    if split and len(selected) > 1:
        # One file per entry
        count = 0
        for p, d in selected:
            d = dict(d)
            if redact_patterns and isinstance(d.get("body"), str):
                d["body"] = _maybe_redact(d["body"], redact_patterns)
            datep = str(d.get("anchor_date") or d.get("created_at") or "").split("T")[0] or "undated"
            label = "DreamEntry" if (d.get("metadata") or {}).get("origin", "").lower() == "dream" else "Entry"
            fname = f"{label}__{_sanitize(str(d.get('title') or p.stem))}__{_sanitize(datep)}{ext}"
            rendered = _render_single(d, fmt, with_meta)
            (dest_dir / fname).write_text(rendered, encoding="utf-8")
            count += 1
        print(f"[OK] Exported {count} entries to {dest_dir}")
        return 0

    # Bundle
    if fmt in ("json", "yaml"):
        bundle = []
        for _, d in selected:
            d2 = dict(d)
            if redact_patterns and isinstance(d2.get("body"), str):
                d2["body"] = _maybe_redact(d2["body"], redact_patterns)
            bundle.append(d2 if with_meta else {k: d2.get(k) for k in ("title", "body") if d2.get(k) is not None})
        if fmt == "json":
            (dest_dir / out_name).write_text(json.dumps(bundle, indent=2), encoding="utf-8")
        else:
            if yaml:
                (dest_dir / out_name).write_text(yaml.safe_dump(bundle, sort_keys=False), encoding="utf-8")
            else:
                (dest_dir / out_name).write_text(json.dumps(bundle, indent=2), encoding="utf-8")
        print(f"[OK] Exported {len(selected)} entries to {dest_dir / out_name}")
        return 0

    # md/txt/pdf/html/rtf combined
    parts = []
    block_fmt = "md" if fmt in ("md", "pdf", "rtf") else ("txt" if fmt == "txt" else fmt)
    for _, d in selected:
        d2 = dict(d)
        if redact_patterns and isinstance(d2.get("body"), str):
            d2["body"] = _maybe_redact(d2["body"], redact_patterns)
        parts.append(_render_single(d2, block_fmt, with_meta))
        parts.append("\n---\n\n")
    content = "".join(parts).rstrip() + "\n"
    (dest_dir / out_name).write_text(content, encoding="utf-8")
    if fmt in ("pdf", "rtf"):
        print(f"[OK] Wrote {fmt.upper()} content (markdown fallback). Use pandoc for conversion if needed: {dest_dir / out_name}")
    else:
        print(f"[OK] Exported to {dest_dir / out_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

