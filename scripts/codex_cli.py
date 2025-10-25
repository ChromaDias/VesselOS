from pathlib import Path
import json
import sys

VERSION = "0.1"

# Try to use Click if available; otherwise fall back to argparse
try:
    import click  # type: ignore
except Exception:  # pragma: no cover
    click = None

# Add repo root to path for codex core imports
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
try:
    from codex.core.export import run as export_run  # type: ignore
except Exception:  # pragma: no cover
    export_run = None


def _init_vault(name: str, base: Path):
    base_path = Path(base)
    vault = base_path / name
    created = False
    if not vault.exists():
        vault.mkdir(parents=True, exist_ok=True)
        created = True
    (vault / "entries").mkdir(exist_ok=True)
    (vault / "exports").mkdir(exist_ok=True)

    cfg_path = vault / "config.json"
    config = {"name": name, "version": VERSION, "anchor_date": None}
    if not cfg_path.exists():
        cfg_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        action = "created"
    else:
        try:
            existing = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
        existing.setdefault("name", name)
        existing["version"] = VERSION
        existing.setdefault("anchor_date", None)
        cfg_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        action = "updated"

    return vault, created, action


if click:

    @click.group(help="Codex memory vault utilities")
    def codex():
        pass

    @codex.command("init", help="Initialize a new codex memory vault")
    @click.option("name", "--name", default="default_codex", help="Name for your new codex directory.")
    @click.option(
        "base",
        "--base",
        type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
        default=Path.cwd(),
        show_default=True,
        help="Base directory in which to create the vault.",
    )
    def init_cmd(name: str, base: Path):
        vault, created, action = _init_vault(name, base)
        click.echo(f"[OK] Codex vault {action}: {vault}")
        if created:
            click.echo("      ├─ entries/\n      ├─ exports/\n      └─ config.json")

    def _load_first_match(entries_dir: Path, key: str):
        candidates = list(entries_dir.glob("*.json"))
        for p in candidates:
            if p.name == key or p.stem == key:
                return p, json.loads(p.read_text(encoding="utf-8"))
        for p in candidates:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            title = str(data.get("title", ""))
            tags = data.get("tags", []) or []
            if key == title or key in tags:
                return p, data
        return None, None

    def _format_entry(data: dict, fmt: str) -> str:
        fmt = (fmt or "json").lower()
        if fmt == "json":
            return json.dumps(data, indent=2)
        if fmt == "yaml":
            try:
                import yaml  # type: ignore
            except Exception:
                return json.dumps(data, indent=2)
            return yaml.safe_dump(data, sort_keys=False)
        if fmt in ("md", "markdown"):
            title = data.get("title", "Untitled")
            created = data.get("created_at", "")
            tags = data.get("tags", [])
            body = data.get("body", "")
            metadata = data.get("metadata", {})
            lines = [f"# {title}", "", f"- Created: {created}", f"- Tags: {', '.join(tags)}", "", "## Body", body]
            if metadata:
                lines += ["", "## Metadata", "```json", json.dumps(metadata, indent=2), "```"]
            return "\n".join(lines)
        if fmt == "txt":
            title = data.get("title", "Untitled")
            created = data.get("created_at", "")
            tags = data.get("tags", [])
            body = data.get("body", "")
            lines = [f"Title: {title}", f"Created: {created}", f"Tags: {', '.join(tags)}", "", body]
            return "\n".join(lines)
        # default fallback
        return json.dumps(data, indent=2)

    def _sanitize(name: str) -> str:
        return "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in name) or "entry"

    @codex.command("summon", help="Retrieve memory artifacts by key or dream filters and optionally export")
    @click.option("--key", "key", required=False, help="Name, file, title, or tag to match")
    @click.option("--dream", is_flag=True, default=False, help="Filter for dream-origin or dream-referenced entries")
    @click.option("--tag", "tag", required=False, help="Symbol/tag to filter when using --dream")
    @click.option("--symbol", "symbol", required=False, help="Search symbolic elements in tags/body/metadata")
    @click.option("--date", "date_str", required=False, help="YYYY-MM-DD to match created_at/anchor_date")
    @click.option("--tone", "tone", required=False, help="Emotional tone to match (metadata.mood)")
    @click.option("--thread", "thread", required=False, help="Restrict to dream entries attached to a named Thread")
    @click.option("--lucid", is_flag=True, default=False, help="Filter to lucid or semi-lucid dreams only")
    @click.option("--contextualize", is_flag=True, default=False, help="Add interpretive layer with cross-references")
    @click.option("--raw", is_flag=True, default=False, help="Return entries as logged (JSON, no interpretation)")
    @click.option("--format", "fmt", default="json", show_default=True, help="Output format: md|txt|json|yaml")
    @click.option("--export", "export", is_flag=True, default=False, help="Write to vault exports/ instead of stdout")
    @click.option(
        "--vault",
        "vault",
        type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
        default=Path.cwd(),
        show_default=True,
        help="Path to an existing vault (directory with config.json and entries/)",
    )
    def summon_cmd(key: str | None, dream: bool, tag: str | None, symbol: str | None, date_str: str | None, tone: str | None, thread: str | None, lucid: bool, contextualize: bool, raw: bool, fmt: str, export: bool, vault: Path):
        vault_path = Path(vault)
        cfg = vault_path / "config.json"
        entries = vault_path / "entries"
        dreams = vault_path / "dreams"
        exports = vault_path / "exports"
        if not (cfg.exists() and entries.exists()):
            raise click.ClickException("Vault not found: expected config.json and entries/ in --vault path")
        # If exporting and no explicit format, default to Markdown
        if export and (fmt is None or fmt.lower() == "json") and not raw:
            fmt = "md"
        def _is_dream(d: dict) -> bool:
            tags = [str(t).lower() for t in (d.get("tags") or [])]
            if any(t in tags for t in ("dream", "dreams", "oneiric", "sleep", "vision")):
                return True
            meta = d.get("metadata") or {}
            # origin field explicitly set to dream
            if str(meta.get("origin", "")).lower() == "dream":
                return True
            for k in ("category", "type", "state"):
                v = str(meta.get(k, "")).lower()
                if "dream" in v or "oneiric" in v:
                    return True
            return False

        def _is_lucid(d: dict) -> bool:
            meta = d.get("metadata") or {}
            if str(meta.get("lucid", "")).lower() in ("true", "yes", "1"):
                return True
            tags = [str(t).lower() for t in (d.get("tags") or [])]
            return any(x in tags for x in ("lucid", "semi-lucid", "semi_lucid"))

        def _has_symbol(d: dict, sym: str) -> bool:
            s = sym.lower()
            tags = [str(t).lower() for t in (d.get("tags") or [])]
            if any(s in t for t in tags):
                return True
            meta = d.get("metadata") or {}
            symbols = meta.get("symbols") or []
            if any(s in str(x).lower() for x in symbols):
                return True
            body = str(d.get("body", "")).lower()
            if s in body:
                return True
            title = str(d.get("title", "")).lower()
            if s in title:
                return True
            return False

        def _has_thread(d: dict, th: str) -> bool:
            t = th.lower()
            meta = d.get("metadata") or {}
            if str(meta.get("thread", "")).lower() == t:
                return True
            threads = meta.get("threads") or []
            if any(str(x).lower() == t for x in threads):
                return True
            tags = [str(x).lower() for x in (d.get("tags") or [])]
            return t in tags

        if dream:
            # Collect and filter all entries from entries/ and dreams/
            matches: list[tuple[Path, dict]] = []
            files = list(entries.glob("*.json"))
            if dreams.exists():
                files += list(dreams.glob("*.json"))
            for p in files:
                try:
                    d = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if not _is_dream(d):
                    continue
                if tag:
                    tset = set(str(t).lower() for t in (d.get("tags") or []))
                    if tag.lower() not in tset:
                        continue
                if symbol and not _has_symbol(d, symbol):
                    continue
                if thread and not _has_thread(d, thread):
                    continue
                if date_str:
                    created = str(d.get("created_at", ""))
                    anchor = str(d.get("anchor_date", ""))
                    if not (created.startswith(date_str) or anchor.startswith(date_str)):
                        continue
                if tone:
                    mood = str((d.get("metadata") or {}).get("mood", "")).lower()
                    if tone.lower() not in mood:
                        continue
                if lucid and not _is_lucid(d):
                    continue
                matches.append((p, d))

            if not matches:
                raise click.ClickException("No dream entries matched the provided filters")

            # If raw -> force JSON output of originals
            if raw:
                rendered = json.dumps([d for _, d in matches], indent=2)
                if export:
                    exports.mkdir(parents=True, exist_ok=True)
                    out_path = exports / "dream_raw.json"
                    out_path.write_text(rendered, encoding="utf-8")
                    click.echo(f"[OK] Exported raw entries to {out_path}")
                else:
                    click.echo(rendered)
                return

            # Render output; contextualize if requested and md/txt
            fmt_l = (fmt or "json").lower()
            if export and fmt_l == "json":
                fmt_l = "md"

            def _linked_logs(ref: dict, all_pairs: list[tuple[Path, dict]], days: int = 3) -> list[str]:
                from datetime import datetime, timedelta
                def _parse(dt: str):
                    try:
                        return datetime.fromisoformat(dt.replace("Z", "+00:00"))
                    except Exception:
                        return None
                ts = _parse(str(ref.get("anchor_date") or ref.get("created_at") or ""))
                if not ts:
                    return []
                lo, hi = ts - timedelta(days=days), ts + timedelta(days=days)
                out = []
                for p, d in all_pairs:
                    if d is ref:
                        continue
                    dt = _parse(str(d.get("anchor_date") or d.get("created_at") or ""))
                    if dt and lo <= dt <= hi:
                        out.append(p.name)
                return out[:10]

            SYMBOL_HINTS = {
                "glass": "vulnerability/clarity/surveillance",
                "cat": "guardianship/intuition/independence",
                "stair": "transition/threshold/dimensional shift",
                "voice": "higher self/external intelligence",
                "water": "emotion/flux/cleansing",
                "mirror": "identity/reflection/dissociation",
            }

            def _contextualize_md(d: dict) -> str:
                base = _format_entry(d, "md")
                if not contextualize:
                    return base
                sym_lines = []
                low_body = str(d.get("body", "")).lower()
                for k, hint in SYMBOL_HINTS.items():
                    if k in low_body or any(k in str(t).lower() for t in (d.get("tags") or [])):
                        sym_lines.append(f"- {k.capitalize()}: {hint}")
                links = _linked_logs(d, matches)
                parts = [base]
                if sym_lines:
                    parts += ["", "## Symbolism", *sym_lines]
                if links:
                    parts += ["", "## Linked Logs", *[f"- \"{n}\"" for n in links]]
                return "\n".join(parts)

            if fmt_l == "json":
                rendered = json.dumps([d for _, d in matches], indent=2)
            elif fmt_l == "yaml":
                try:
                    import yaml  # type: ignore
                    rendered = yaml.safe_dump([d for _, d in matches], sort_keys=False)
                except Exception:
                    rendered = json.dumps([d for _, d in matches], indent=2)
            elif fmt_l in ("md", "markdown"):
                parts = []
                for _, d in matches:
                    parts.append(_contextualize_md(d) if contextualize else _format_entry(d, "md"))
                    parts.append("\n---\n")
                rendered = "\n".join(parts).rstrip()
            else:  # txt or default
                parts = []
                for _, d in matches:
                    parts.append(_format_entry(d, "txt"))
                    parts.append("\n---\n")
                rendered = "\n".join(parts).rstrip()

            if export:
                exports.mkdir(parents=True, exist_ok=True)
                ext = {"json": ".json", "yaml": ".yaml", "yml": ".yaml", "md": ".md", "markdown": ".md", "txt": ".txt"}.get(fmt_l, ".txt")
                if len(matches) == 1:
                    _, d0 = matches[0]
                    title = str(d0.get("title") or "DreamEntry")
                    datep = str(d0.get("anchor_date") or d0.get("created_at") or "").split("T")[0]
                    fname = f"DreamEntry__{_sanitize(title)}__{_sanitize(datep or 'undated')}{ext}"
                    out_path = exports / fname
                    out_path.write_text(rendered, encoding="utf-8")
                    click.echo(f"[OK] Exported to {out_path}")
                else:
                    parts = ["DreamEntries"]
                    if tag: parts.append(f"tag-{_sanitize(tag)}")
                    if symbol: parts.append(f"symbol-{_sanitize(symbol)}")
                    if date_str: parts.append(f"date-{_sanitize(date_str)}")
                    if tone: parts.append(f"tone-{_sanitize(tone)}")
                    if thread: parts.append(f"thread-{_sanitize(thread)}")
                    if lucid: parts.append("lucid")
                    fname = "__".join(parts) + ext
                    out_path = exports / fname
                    out_path.write_text(rendered, encoding="utf-8")
                    click.echo(f"[OK] Exported {len(matches)} dream entries to {out_path}")
            else:
                click.echo(rendered)
            return

        # Legacy single-key behavior
        if not key:
            raise click.ClickException("--key is required unless using --dream filters")
        p, data = _load_first_match(entries, key)
        if not p:
            raise click.ClickException(f"No entry found matching key: {key}")
        rendered = _format_entry(data, fmt)
        if export:
            exports.mkdir(parents=True, exist_ok=True)
            ext = {"json": ".json", "yaml": ".yaml", "yml": ".yaml", "md": ".md", "markdown": ".md", "txt": ".txt"}.get(fmt.lower(), ".txt")
            base = _sanitize(key if key else p.stem)
            out_path = exports / f"{base}{ext}"
            out_path.write_text(rendered, encoding="utf-8")
            click.echo(f"[OK] Exported to {out_path}")
        else:
            click.echo(rendered)

    @codex.command("echo", help="Resonance-based retrieval of past entries")
    @click.option("--phrase", "phrase", required=False, help="Quoted phrase to search in body/title")
    @click.option("--tag", "tag", required=False, help="Symbolic tag to search for")
    @click.option("--tone", "tone", required=False, help="Emotional tone to search (metadata.mood)")
    @click.option("--type", "typ", required=False, type=click.Choice(["dream", "log", "fragment", "event", "entry"], case_sensitive=False))
    @click.option("--from", "from_", required=False, type=click.Choice(["dream"], case_sensitive=False), help="Activate dream memory matching mode")
    @click.option("--symbol", "symbol", required=False, help="Search by visual dream motif or sigil")
    @click.option("--feeling", "feeling", required=False, help="Synonym for --tone")
    @click.option("--echo-depth", "echo_depth", default=1, show_default=True, help="Recursive depth for linked dream fragments (1-3)")
    @click.option("--fuzzy", is_flag=True, default=False, help="Enable approximate matching")
    @click.option("--limit", "limit", default=3, show_default=True, help="Max results to return (max 10)")
    @click.option("--sort", "sort_by", default="resonance", show_default=True, type=click.Choice(["resonance", "date"], case_sensitive=False))
    @click.option("--vault", "vault", type=click.Path(file_okay=False, dir_okay=True, path_type=Path), default=Path.cwd(), show_default=True, help="Path to a vault")
    def echo_cmd(phrase: str | None, tag: str | None, tone: str | None, typ: str | None, from_: str | None, symbol: str | None, feeling: str | None, echo_depth: int, fuzzy: bool, limit: int, sort_by: str, vault: Path):
        from difflib import SequenceMatcher
        vault_path = Path(vault)
        entries = vault_path / "entries"
        dreams = vault_path / "dreams"
        cfg = vault_path / "config.json"
        if not (cfg.exists() and entries.exists()):
            raise click.ClickException("Vault not found: expected config.json and entries/ in --vault path")
        # Normalize parameters
        if feeling and not tone:
            tone = feeling
        dream_mode = (from_ or "").lower() == "dream"
        try:
            echo_depth = max(1, min(3, int(echo_depth)))
        except Exception:
            echo_depth = 1
        limit = max(1, min(10, int(limit)))

        def _is_dream(d: dict) -> bool:
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

        def get_type(d: dict) -> str:
            if _is_dream(d):
                return "dream"
            meta = d.get("metadata") or {}
            t = str(meta.get("type", "") or d.get("type", "")).lower()
            return t or "entry"

        def get_date(d: dict) -> str:
            return str(d.get("anchor_date") or d.get("created_at") or "")

        def reson_score(d: dict) -> float:
            score = 0.0
            text = (str(d.get("title", "")) + "\n" + str(d.get("body", ""))).lower()
            tags = [str(t).lower() for t in (d.get("tags") or [])]
            meta = d.get("metadata") or {}
            mood = str(meta.get("mood", "")).lower()
            symbols = [str(x).lower() for x in (meta.get("symbols") or [])]
            if phrase:
                p = phrase.lower()
                if p in text:
                    score += 0.6
                elif fuzzy:
                    # compare with title and body segments
                    ratio_t = SequenceMatcher(None, p, str(d.get("title", "")).lower()).ratio()
                    ratio_b = SequenceMatcher(None, p, text[:2000]).ratio()
                    score += 0.4 * max(ratio_t, ratio_b)
            if tag:
                t = tag.lower()
                if t in tags or any(t in s for s in symbols) or (fuzzy and t in text):
                    score += 0.3
                else:
                    score -= 0.2
            if tone:
                t = tone.lower()
                if t in mood or (fuzzy and t in text):
                    score += 0.2
                else:
                    score -= 0.1
            if typ:
                score += 0.1 if get_type(d) == typ.lower() else -0.3
            # small bonus for recency if sorting by resonance
            dt = get_date(d)
            if dt:
                score += 0.01
            return max(score, 0.0)

        files = list(entries.glob("*.json"))
        if dreams.exists():
            files += list(dreams.glob("*.json"))

        pairs: list[tuple[Path, dict]] = []
        for p in files:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            # Dream-mode restricts to dream entries
            if dream_mode and get_type(data) != "dream":
                continue
            # Type hard filter if provided
            if typ and get_type(data) != typ.lower():
                continue
            # Tag/tone hard filters if provided and not fuzzy? choose soft filter -> require presence
            if tag:
                t = tag.lower()
                tags_l = [str(ti).lower() for ti in (data.get("tags") or [])]
                meta = data.get("metadata") or {}
                symbols = [str(x).lower() for x in (meta.get("symbols") or [])]
                text = (str(data.get("title", "")) + "\n" + str(data.get("body", ""))).lower()
                if not (t in tags_l or any(t in s for s in symbols) or (fuzzy and t in text)):
                    continue
            if tone:
                m = str((data.get("metadata") or {}).get("mood", "")).lower()
                text = (str(data.get("title", "")) + "\n" + str(data.get("body", ""))).lower()
                if not (tone.lower() in m or (fuzzy and tone.lower() in text)):
                    continue
            if symbol:
                s = symbol.lower()
                tags_l = [str(ti).lower() for ti in (data.get("tags") or [])]
                meta = data.get("metadata") or {}
                symbols_l = [str(x).lower() for x in (meta.get("symbols") or [])]
                text = (str(data.get("title", "")) + "\n" + str(data.get("body", ""))).lower()
                if not (any(s in t for t in tags_l) or any(s in x for x in symbols_l) or s in text or (fuzzy and s in text)):
                    continue
            pairs.append((p, data))

        if not pairs:
            click.echo("No echoes found.")
            return

        # Boost resonance with symbol matching
        def symbol_boost(d: dict) -> float:
            if not symbol:
                return 0.0
            s = str(symbol).lower()
            tags_l = [str(ti).lower() for ti in (d.get("tags") or [])]
            meta = d.get("metadata") or {}
            symbols_l = [str(x).lower() for x in (meta.get("symbols") or [])]
            text = (str(d.get("title", "")) + "\n" + str(d.get("body", ""))).lower()
            if any(s in t for t in tags_l) or any(s in x for x in symbols_l):
                return 0.25
            if fuzzy and s in text:
                return 0.15
            return 0.0

        scored = [
            (reson_score(d) + symbol_boost(d), p, d) for p, d in pairs
        ]

        if sort_by.lower() == "date":
            def dt_key(item):
                _, pth, dat = item
                return get_date(dat)
            scored.sort(key=dt_key, reverse=True)
        else:
            scored.sort(key=lambda x: x[0], reverse=True)

        top = scored[: max(1, int(limit))]

        # Dream-mode: optionally include shallow references (echo depth)
        ref_map = {}
        if dream_mode and echo_depth > 1:
            # Build candidate set for references
            all_dream_pairs = [(p, d) for p, d in pairs if get_type(d) == "dream"]
            def _linked(ref: dict):
                from datetime import datetime, timedelta
                def _parse(dt: str):
                    try:
                        return datetime.fromisoformat(dt.replace("Z", "+00:00"))
                    except Exception:
                        return None
                ts = _parse(str(ref.get("anchor_date") or ref.get("created_at") or ""))
                tags_ref = set(str(t).lower() for t in (ref.get("tags") or []))
                sym_ref = set(str(x).lower() for x in ((ref.get("metadata") or {}).get("symbols") or []))
                links = []
                for p, d in all_dream_pairs:
                    if d is ref:
                        continue
                    # date window
                    ok_date = False
                    if ts:
                        dt = _parse(str(d.get("anchor_date") or d.get("created_at") or ""))
                        if dt:
                            ok_date = abs((dt - ts).days) <= 3
                    # tag/symbol overlap
                    tags_d = set(str(t).lower() for t in (d.get("tags") or []))
                    sym_d = set(str(x).lower() for x in ((d.get("metadata") or {}).get("symbols") or []))
                    ok_overlap = bool(tags_ref & tags_d or sym_ref & sym_d)
                    if ok_date or ok_overlap:
                        links.append(p.name)
                return links[:10]
            for score, pth, dat in top:
                ref_map[pth.name] = _linked(dat)

        # Render textual summary
        def excerpt(text: str, length: int = 120) -> str:
            t = " ".join(text.split())
            return (t[: length - 1] + "…") if len(t) > length else t

        heading = "Codex Echo (Dream Mode)" if dream_mode else "# Codex Echo Results (" + ("Resonance" if sort_by.lower()=="resonance" else "Date") + " Sort)"
        lines = [heading if dream_mode else heading]
        if phrase:
            lines.append(f"Matched: \"{phrase}\" | Fuzzy: {'Enabled' if fuzzy else 'Disabled'}" + (f" | Tone: {tone}" if tone else ""))
        elif tag or tone or typ:
            meta = []
            if tag: meta.append(f"Tag: {tag}")
            if tone: meta.append(f"Tone: {tone}")
            if typ: meta.append(f"Type: {typ}")
            if symbol: meta.append(f"Symbol: {symbol}")
            if dream_mode: meta.append("From: dream")
            lines.append("Filters: " + ", ".join(meta))
        lines.append("")

        idx = 1
        for score, path_i, data in top:
            label_type = get_type(data).capitalize()
            dt = get_date(data).split("T")[0]
            title = str(data.get("title") or path_i.stem)
            body = str(data.get("body") or "")
            tags_l = data.get("tags") or []
            mood = (data.get("metadata") or {}).get("mood")
            res_pct = int(round(min(1.0, score) * 100))
            lines.append(f"{idx}. {label_type}: {title}")
            if dt:
                lines.append(f"   - Logged: {dt}")
            if tags_l:
                lines.append(f"   - Tags: {', '.join(tags_l)}")
            if mood:
                lines.append(f"   - Tone: {mood}")
            if sort_by.lower() == "resonance":
                lines.append(f"   - Resonance: {res_pct}%")
            if body:
                lines.append(f"   - Excerpt: \"{excerpt(body)}\"")
            if dream_mode and echo_depth > 1:
                refs = ref_map.get(path_i.name) or []
                if refs:
                    lines.append(f"   - Echo Depth: 1 → references [{', '.join(refs)}]")
            lines.append("")
            idx += 1

        lines.append("Use \"codex open <entry_id>\" to review.")
        click.echo("\n".join(lines))

    @codex.command("export", help="Export an entry or collection into a portable format")
    @click.argument("target")
    @click.option("--format", "fmt", default="md", show_default=True,
                  type=click.Choice(["md", "txt", "json", "yaml", "pdf", "rtf", "html"], case_sensitive=False))
    @click.option("--with-metadata", is_flag=True, default=False, help="Include metadata, timestamps, tags, authors")
    @click.option("--output", "output", required=False, help="Output filename (written under exports/)")
    @click.option("--vault", "vault", type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
                  default=Path.cwd(), show_default=True, help="Path to a vault")
    def export_cmd(target: str, fmt: str, with_metadata: bool, output: str | None, vault: Path):
        if export_run is None:
            raise click.ClickException("Export module unavailable")
        rc = export_run(target, fmt, with_metadata, output, Path(vault))
        if rc != 0:
            raise click.ClickException("Export failed")

    @codex.command("list", help="List entries from the vault with optional filters")
    @click.option("--tag", "tag", required=False)
    @click.option("--date", "date_str", required=False, help="YYYY-MM-DD prefix to match created/anchor date")
    @click.option("--type", "typ", required=False, type=click.Choice(["dream", "log", "fragment", "event", "entry"], case_sensitive=False))
    @click.option("--vault", "vault", type=click.Path(file_okay=False, dir_okay=True, path_type=Path), default=Path.cwd(), show_default=True)
    def list_cmd(tag: str | None, date_str: str | None, typ: str | None, vault: Path):
        try:
            from codex.core.indexer import list_entries  # type: ignore
        except Exception as e:
            raise click.ClickException(f"Indexer unavailable: {e}")
        rows = list_entries(Path(vault), tag=tag, date=date_str, typ=typ)
        if not rows:
            click.echo("(no entries)")
            return
        for fname, it in rows:
            dt = (it.get("anchor_date") or it.get("created_at") or "").split("T")[0]
            title = it.get("title") or fname
            tags = ", ".join(it.get("tags") or [])
            click.echo(f"- {dt:10s} [{it.get('type')}] {title}  (tags: {tags})  -> {fname}")

    @codex.command("index", help="Rebuild the vault index")
    @click.option("--vault", "vault", type=click.Path(file_okay=False, dir_okay=True, path_type=Path), default=Path.cwd(), show_default=True)
    def index_cmd(vault: Path):
        try:
            from codex.core.indexer import build_index  # type: ignore
        except Exception as e:
            raise click.ClickException(f"Indexer unavailable: {e}")
        p = build_index(Path(vault))
        click.echo(f"[OK] Rebuilt index at {p}")

    @codex.command("add", help="Create a new entry in the vault")
    @click.option("--title", required=True)
    @click.option("--body", required=True)
    @click.option("--tags", "tags_csv", required=False, help="Comma-separated tags")
    @click.option("--date", "date_str", required=False, help="Anchor/created date (YYYY-MM-DD)")
    @click.option("--dream", is_flag=True, default=False, help="Store under dreams/ and mark origin=dream")
    @click.option("--vault", "vault", type=click.Path(file_okay=False, dir_okay=True, path_type=Path), default=Path.cwd(), show_default=True)
    def add_cmd(title: str, body: str, tags_csv: str | None, date_str: str | None, dream: bool, vault: Path):
        try:
            from codex.core.schema import validate_entry  # type: ignore
        except Exception:
            def validate_entry(_) -> bool:  # type: ignore
                return True
        tags = [t.strip() for t in (tags_csv or "").split(",") if t.strip()]
        entry = {
            "title": title,
            "tags": tags,
            "created_at": date_str or "",
            "anchor_date": date_str or "",
            "body": body,
            "metadata": {"origin": "dream"} if dream else {},
        }
        if not validate_entry(entry):
            raise click.ClickException("Entry does not conform to schema (title/body required)")
        vault_path = Path(vault)
        target_dir = vault_path / ("dreams" if dream else "entries")
        target_dir.mkdir(parents=True, exist_ok=True)
        import re
        date_part = (date_str or "undated").replace(":", "-")
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", title).strip("_") or "entry"
        fname = f"codex_{date_part}_{slug}.json"
        out_path = target_dir / fname
        i = 1
        while out_path.exists():
            out_path = target_dir / f"codex_{date_part}_{slug}_{i}.json"
            i += 1
        out_path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
        try:
            from codex.core.indexer import build_index  # type: ignore
            build_index(vault_path)
        except Exception:
            pass
        click.echo(f"[OK] Created {out_path}")

    @codex.command("update", help="Modify or expand an entry by pattern replacement")
    @click.argument("target")
    @click.option("--pattern", "pattern", required=True, help="Regex pattern to search for")
    @click.option("--replacement", "replacement", required=True, help="Replacement text")
    @click.option("--multiple", is_flag=True, default=False, help="Replace all matches instead of the first only")
    @click.option(
        "--vault",
        "vault",
        type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
        default=Path.cwd(),
        show_default=True,
        help="Path to an existing vault (directory with config.json and entries/)",
    )
    def update_cmd(target: str, pattern: str, replacement: str, multiple: bool, vault: Path):
        import re
        from datetime import datetime, timezone
        vault_path = Path(vault)
        cfg = vault_path / "config.json"
        entries = vault_path / "entries"
        dreams = vault_path / "dreams"
        if not (cfg.exists() and entries.exists()):
            raise click.ClickException("Vault not found: expected config.json and entries/ in --vault path")

        files = list(entries.glob("*.json"))
        if dreams.exists():
            files += list(dreams.glob("*.json"))

        def matches_key(p: Path, data: dict) -> bool:
            if p.name == target or p.stem == target:
                return True
            title = str(data.get("title", ""))
            if target == title:
                return True
            tags = [str(t) for t in (data.get("tags") or [])]
            return target in tags

        candidates: list[tuple[Path, dict]] = []
        for p in files:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if matches_key(p, data):
                candidates.append((p, data))

        if not candidates:
            raise click.ClickException(f"No entry found matching: {target}")
        if len(candidates) > 1:
            names = ", ".join(p.name for p, _ in candidates[:10])
            raise click.ClickException(f"Multiple entries match '{target}'. Be more specific. Candidates: {names} ...")

        p, data = candidates[0]
        flags = re.MULTILINE | re.DOTALL
        total = 0
        # Replace in title then body (first match overall unless --multiple)
        if isinstance(data.get("title"), str):
            new_title, n = re.subn(pattern, replacement, data["title"], 0 if multiple else 1, flags=flags)
            if n:
                data["title"] = new_title
                total += n
        if isinstance(data.get("body"), str) and (multiple or total == 0):
            new_body, n = re.subn(pattern, replacement, data["body"], 0 if multiple else 1, flags=flags)
            if n:
                data["body"] = new_body
                total += n

        if total == 0:
            click.echo("No changes applied (pattern not found).")
            return

        meta = data.get("metadata") or {}
        meta["last_updated"] = datetime.now(timezone.utc).isoformat()
        data["metadata"] = meta

        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        click.echo(f"[OK] Updated {p.name} (replacements: {total})")

    def main(argv=None):
        return codex.main(args=argv, prog_name="codex")

else:  # Fallback minimal CLI

    def main(argv=None):
        import argparse

        parser = argparse.ArgumentParser(prog="codex", description="Codex memory vault utilities")
        sub = parser.add_subparsers(dest="cmd", required=True)

        p_init = sub.add_parser("init", help="Initialize a new codex memory vault")
        p_init.add_argument("--name", default="default_codex")
        p_init.add_argument("--base", default=str(Path.cwd()))

        p_summon = sub.add_parser("summon", help="Retrieve memory artifacts by key or dream filters and optionally export")
        p_summon.add_argument("--key", required=False)
        p_summon.add_argument("--dream", action="store_true")
        p_summon.add_argument("--tag")
        p_summon.add_argument("--symbol")
        p_summon.add_argument("--date", dest="date_str")
        p_summon.add_argument("--tone")
        p_summon.add_argument("--thread")
        p_summon.add_argument("--lucid", action="store_true")
        p_summon.add_argument("--contextualize", action="store_true")
        p_summon.add_argument("--raw", action="store_true")
        p_summon.add_argument("--format", dest="fmt", default="json")
        p_summon.add_argument("--export", dest="export", action="store_true")
        p_summon.add_argument("--vault", default=str(Path.cwd()))

        p_echo = sub.add_parser("echo", help="Resonance-based retrieval of past entries")
        p_echo.add_argument("--phrase")
        p_echo.add_argument("--tag")
        p_echo.add_argument("--tone")
        p_echo.add_argument("--type", dest="typ", choices=["dream", "log", "fragment", "event", "entry"])
        p_echo.add_argument("--from", dest="from_", choices=["dream"])
        p_echo.add_argument("--symbol")
        p_echo.add_argument("--feeling")
        p_echo.add_argument("--echo-depth", dest="echo_depth", type=int, default=1)
        p_echo.add_argument("--fuzzy", action="store_true")
        p_echo.add_argument("--limit", type=int, default=3)
        p_echo.add_argument("--sort", dest="sort_by", choices=["resonance", "date"], default="resonance")
        p_echo.add_argument("--vault", default=str(Path.cwd()))

        p_update = sub.add_parser("update", help="Modify or expand an entry by pattern replacement")
        p_update.add_argument("target")
        p_update.add_argument("--pattern", required=True)
        p_update.add_argument("--replacement", required=True)
        p_update.add_argument("--multiple", action="store_true")
        p_update.add_argument("--vault", default=str(Path.cwd()))

        p_export = sub.add_parser("export", help="Export an entry or collection into a portable format")
        p_export.add_argument("target")
        p_export.add_argument("--format", dest="fmt", default="md", choices=["md","txt","json","yaml","pdf","rtf","html"])
        p_export.add_argument("--with-metadata", dest="with_metadata", action="store_true")
        p_export.add_argument("--output")
        p_export.add_argument("--vault", default=str(Path.cwd()))

        p_list = sub.add_parser("list", help="List entries with optional filters")
        p_list.add_argument("--tag")
        p_list.add_argument("--date", dest="date_str")
        p_list.add_argument("--type", dest="typ", choices=["dream", "log", "fragment", "event", "entry"])
        p_list.add_argument("--vault", default=str(Path.cwd()))

        p_index = sub.add_parser("index", help="Rebuild the vault index")
        p_index.add_argument("--vault", default=str(Path.cwd()))

        p_add = sub.add_parser("add", help="Create a new entry")
        p_add.add_argument("--title", required=True)
        p_add.add_argument("--body", required=True)
        p_add.add_argument("--tags", dest="tags_csv")
        p_add.add_argument("--date", dest="date_str")
        p_add.add_argument("--dream", action="store_true")
        p_add.add_argument("--vault", default=str(Path.cwd()))

        args = parser.parse_args(argv)
        if args.cmd == "init":
            vault, created, action = _init_vault(args.name, Path(args.base))
            print(f"[OK] Codex vault {action}: {vault}")
            if created:
                print("      ├─ entries/\n      ├─ exports/\n      └─ config.json")
        elif args.cmd == "summon":
            vault_path = Path(args.vault)
            cfg = vault_path / "config.json"
            entries = vault_path / "entries"
            exports = vault_path / "exports"
            if not (cfg.exists() and entries.exists()):
                print("[ERR] Vault not found: expected config.json and entries/ in --vault path", file=sys.stderr)
                return 2
            # reuse internal helpers via minimal copies
            def _load_first_match(entries_dir: Path, key: str):
                candidates = list(entries_dir.glob("*.json"))
                for p in candidates:
                    if p.name == key or p.stem == key:
                        return p, json.loads(p.read_text(encoding="utf-8"))
                for p in candidates:
                    try:
                        data = json.loads(p.read_text(encoding="utf-8"))
                    except Exception:
                        continue
                    title = str(data.get("title", ""))
                    tags = data.get("tags", []) or []
                    if args.key == title or args.key in tags:
                        return p, data
                return None, None

            def _format_entry(data: dict, fmt: str) -> str:
                fmt = (fmt or "json").lower()
                if fmt == "json":
                    return json.dumps(data, indent=2)
                if fmt == "yaml":
                    try:
                        import yaml  # type: ignore
                    except Exception:
                        return json.dumps(data, indent=2)
                    return yaml.safe_dump(data, sort_keys=False)
                if fmt in ("md", "markdown"):
                    title = data.get("title", "Untitled")
                    created = data.get("created_at", "")
                    tags = data.get("tags", [])
                    body = data.get("body", "")
                    metadata = data.get("metadata", {})
                    lines = [f"# {title}", "", f"- Created: {created}", f"- Tags: {', '.join(tags)}", "", "## Body", body]
                    if metadata:
                        lines += ["", "## Metadata", "```json", json.dumps(metadata, indent=2), "```"]
                    return "\n".join(lines)
                if fmt == "txt":
                    title = data.get("title", "Untitled")
                    created = data.get("created_at", "")
                    tags = data.get("tags", [])
                    body = data.get("body", "")
                    lines = [f"Title: {title}", f"Created: {created}", f"Tags: {', '.join(tags)}", "", body]
                    return "\n".join(lines)
                return json.dumps(data, indent=2)
            # Dream flow
            if args.dream:
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

                matches = []
                files = list(entries.glob("*.json"))
                dreams = vault_path / "dreams"
                if dreams.exists():
                    files += list(dreams.glob("*.json"))
                for p in files:
                    try:
                        d = json.loads(p.read_text(encoding="utf-8"))
                    except Exception:
                        continue
                    if not is_dream(d):
                        continue
                    if args.tag:
                        tset = set(str(t).lower() for t in (d.get("tags") or []))
                        if args.tag.lower() not in tset:
                            continue
                    if args.symbol:
                        s = args.symbol.lower()
                        tags = [str(t).lower() for t in (d.get("tags") or [])]
                        meta = d.get("metadata") or {}
                        symbols = [str(x).lower() for x in (meta.get("symbols") or [])]
                        body = str(d.get("body", "")).lower()
                        title = str(d.get("title", "")).lower()
                        if not (any(s in t for t in tags) or any(s in x for x in symbols) or s in body or s in title):
                            continue
                    if args.date_str:
                        created = str(d.get("created_at", ""))
                        anchor = str(d.get("anchor_date", ""))
                        if not (created.startswith(args.date_str) or anchor.startswith(args.date_str)):
                            continue
                    if args.tone:
                        mood = str((d.get("metadata") or {}).get("mood", "")).lower()
                        if args.tone.lower() not in mood:
                            continue
                    if args.thread:
                        t = args.thread.lower()
                        meta = d.get("metadata") or {}
                        if not (
                            str(meta.get("thread", "")).lower() == t or
                            t in [str(x).lower() for x in (meta.get("threads") or [])] or
                            t in [str(x).lower() for x in (d.get("tags") or [])]
                        ):
                            continue
                    if args.lucid:
                        meta = d.get("metadata") or {}
                        lucid_val = str(meta.get("lucid", "")).lower() in ("true", "yes", "1")
                        tset = set(str(t).lower() for t in (d.get("tags") or []))
                        if not (lucid_val or "lucid" in tset or "semi-lucid" in tset or "semi_lucid" in tset):
                            continue
                    matches.append((p, d))

                if not matches:
                    print("[ERR] No dream entries matched the provided filters", file=sys.stderr)
                    return 1

                fmt_l = (args.fmt or "json").lower()
                if args.export and fmt_l == "json" and not args.raw:
                    fmt_l = "md"
                if fmt_l == "json":
                    rendered = json.dumps([d for _, d in matches], indent=2)
                elif fmt_l == "yaml":
                    try:
                        import yaml  # type: ignore
                        rendered = yaml.safe_dump([d for _, d in matches], sort_keys=False)
                    except Exception:
                        rendered = json.dumps([d for _, d in matches], indent=2)
                elif fmt_l in ("md", "markdown"):
                    SYMBOL_HINTS = {
                        "glass": "vulnerability/clarity/surveillance",
                        "cat": "guardianship/intuition/independence",
                        "stair": "transition/threshold/dimensional shift",
                        "voice": "higher self/external intelligence",
                        "water": "emotion/flux/cleansing",
                        "mirror": "identity/reflection/dissociation",
                    }
                    def linked_logs(ref: dict, all_pairs):
                        from datetime import datetime, timedelta
                        def _parse(dt: str):
                            try:
                                return datetime.fromisoformat(dt.replace("Z", "+00:00"))
                            except Exception:
                                return None
                        ts = _parse(str(ref.get("anchor_date") or ref.get("created_at") or ""))
                        if not ts:
                            return []
                        lo, hi = ts - timedelta(days=3), ts + timedelta(days=3)
                        out = []
                        for p, d in all_pairs:
                            if d is ref:
                                continue
                            dt = _parse(str(d.get("anchor_date") or d.get("created_at") or ""))
                            if dt and lo <= dt <= hi:
                                out.append(p.name)
                        return out[:10]
                    parts = []
                    for _, d in matches:
                        base = _format_entry(d, "md")
                        if args.contextualize:
                            sym_lines = []
                            low_body = str(d.get("body", "")).lower()
                            tags = [str(t).lower() for t in (d.get("tags") or [])]
                            for k, hint in SYMBOL_HINTS.items():
                                if k in low_body or any(k in t for t in tags):
                                    sym_lines.append(f"- {k.capitalize()}: {hint}")
                            links = linked_logs(d, matches)
                            if sym_lines:
                                base += "\n\n## Symbolism\n" + "\n".join(sym_lines)
                            if links:
                                base += "\n\n## Linked Logs\n" + "\n".join(f"- \"{n}\"" for n in links)
                        parts.append(base)
                        parts.append("\n---\n")
                    rendered = "\n".join(parts).rstrip()
                else:
                    parts = []
                    for _, d in matches:
                        parts.append(_format_entry(d, "txt"))
                        parts.append("\n---\n")
                    rendered = "\n".join(parts).rstrip()

                if args.raw:
                    if args.export:
                        out_path = exports / "dream_raw.json"
                        out_path.write_text(rendered if isinstance(rendered, str) else json.dumps([d for _, d in matches], indent=2), encoding="utf-8")
                        print(f"[OK] Exported raw entries to {out_path}")
                    else:
                        print(json.dumps([d for _, d in matches], indent=2))
                    return 0

                if args.export:
                    exports.mkdir(parents=True, exist_ok=True)
                    ext = {"json": ".json", "yaml": ".yaml", "yml": ".yaml", "md": ".md", "markdown": ".md", "txt": ".txt"}.get(fmt_l, ".txt")
                    if len(matches) == 1:
                        _, d0 = matches[0]
                        title = str(d0.get("title") or "DreamEntry")
                        datep = str(d0.get("anchor_date") or d0.get("created_at") or "").split("T")[0]
                        fname = f"DreamEntry__{''.join(c if c.isalnum() or c in ('-','_','.') else '_' for c in title)}__{''.join(c if c.isalnum() or c in ('-','_','.') else '_' for c in (datep or 'undated'))}{ext}"
                        out_path = exports / fname
                        out_path.write_text(rendered, encoding="utf-8")
                        print(f"[OK] Exported to {out_path}")
                    else:
                        parts = ["DreamEntries"]
                        if args.tag: parts.append(f"tag-{''.join(c if c.isalnum() or c in ('-','_','.') else '_' for c in args.tag)}")
                        if args.symbol: parts.append(f"symbol-{''.join(c if c.isalnum() or c in ('-','_','.') else '_' for c in args.symbol)}")
                        if args.date_str: parts.append(f"date-{''.join(c if c.isalnum() or c in ('-','_','.') else '_' for c in args.date_str)}")
                        if args.tone: parts.append(f"tone-{''.join(c if c.isalnum() or c in ('-','_','.') else '_' for c in args.tone)}")
                        if args.thread: parts.append(f"thread-{''.join(c if c.isalnum() or c in ('-','_','.') else '_' for c in args.thread)}")
                        if args.lucid: parts.append("lucid")
                        fname = "__".join(parts) + ext
                        out_path = exports / fname
                        out_path.write_text(rendered, encoding="utf-8")
                        print(f"[OK] Exported {len(matches)} dream entries to {out_path}")
                else:
                    print(rendered)
                return 0

            # Key flow
            if not args.key:
                print("[ERR] --key is required unless using --dream filters", file=sys.stderr)
                return 2
            p, data = _load_first_match(entries, args.key)
            if not p:
                print(f"[ERR] No entry found matching key: {args.key}", file=sys.stderr)
                return 1
            rendered = _format_entry(data, args.fmt)
            if args.export:
                exports.mkdir(parents=True, exist_ok=True)
                ext = {"json": ".json", "yaml": ".yaml", "yml": ".yaml", "md": ".md", "markdown": ".md", "txt": ".txt"}.get(args.fmt.lower(), ".txt")
                base = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in (args.key or p.stem)) or "entry"
                out_path = exports / f"{base}{ext}"
                out_path.write_text(rendered, encoding="utf-8")
                print(f"[OK] Exported to {out_path}")
            else:
                print(rendered)
            return 0
        elif args.cmd == "echo":
            from difflib import SequenceMatcher
            vault_path = Path(args.vault)
            entries = vault_path / "entries"
            dreams = vault_path / "dreams"
            cfg = vault_path / "config.json"
            if not (cfg.exists() and entries.exists()):
                print("Vault not found: expected config.json and entries/ in --vault path", file=sys.stderr)
                return 2
            # Normalize
            tone = args.tone or args.feeling
            dream_mode = (args.from_ or '').lower() == 'dream'
            try:
                echo_depth = max(1, min(3, int(args.echo_depth)))
            except Exception:
                echo_depth = 1
            limit = max(1, min(10, int(args.limit)))

            def _is_dream(d: dict) -> bool:
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

            def get_type(d: dict) -> str:
                if _is_dream(d):
                    return "dream"
                meta = d.get("metadata") or {}
                t = str(meta.get("type", "") or d.get("type", "")).lower()
                return t or "entry"

            def get_date(d: dict) -> str:
                return str(d.get("anchor_date") or d.get("created_at") or "")

            def reson_score(d: dict) -> float:
                score = 0.0
                text = (str(d.get("title", "")) + "\n" + str(d.get("body", ""))).lower()
                tags = [str(t).lower() for t in (d.get("tags") or [])]
                meta = d.get("metadata") or {}
                mood = str(meta.get("mood", "")).lower()
                symbols = [str(x).lower() for x in (meta.get("symbols") or [])]
                if args.phrase:
                    p = args.phrase.lower()
                    if p in text:
                        score += 0.6
                    elif args.fuzzy:
                        ratio_t = SequenceMatcher(None, p, str(d.get("title", "")).lower()).ratio()
                        ratio_b = SequenceMatcher(None, p, text[:2000]).ratio()
                        score += 0.4 * max(ratio_t, ratio_b)
                if args.tag:
                    t = args.tag.lower()
                    if t in tags or any(t in s for s in symbols) or (args.fuzzy and t in text):
                        score += 0.3
                    else:
                        score -= 0.2
                if args.tone:
                    t = args.tone.lower()
                    if t in mood or (args.fuzzy and t in text):
                        score += 0.2
                    else:
                        score -= 0.1
                if args.typ:
                    score += 0.1 if get_type(d) == args.typ.lower() else -0.3
                dt = get_date(d)
                if dt:
                    score += 0.01
                return max(score, 0.0)

            files = list(entries.glob("*.json"))
            if dreams.exists():
                files += list(dreams.glob("*.json"))
            pairs: list[tuple[Path, dict]] = []
            for p in files:
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if dream_mode and get_type(data) != 'dream':
                    continue
                if args.typ and get_type(data) != args.typ.lower():
                    continue
                if args.tag:
                    t = args.tag.lower()
                    tags_l = [str(ti).lower() for ti in (data.get("tags") or [])]
                    meta = data.get("metadata") or {}
                    symbols = [str(x).lower() for x in (meta.get("symbols") or [])]
                    text = (str(data.get("title", "")) + "\n" + str(data.get("body", ""))).lower()
                    if not (t in tags_l or any(t in s for s in symbols) or (args.fuzzy and t in text)):
                        continue
                if tone:
                    m = str((data.get("metadata") or {}).get("mood", "")).lower()
                    text = (str(data.get("title", "")) + "\n" + str(data.get("body", ""))).lower()
                    if not ((tone or '').lower() in m or (args.fuzzy and (tone or '').lower() in text)):
                        continue
                if args.symbol:
                    s = args.symbol.lower()
                    tags_l = [str(ti).lower() for ti in (data.get("tags") or [])]
                    meta = data.get("metadata") or {}
                    symbols_l = [str(x).lower() for x in (meta.get("symbols") or [])]
                    text = (str(data.get("title", "")) + "\n" + str(data.get("body", ""))).lower()
                    if not (any(s in t for t in tags_l) or any(s in x for x in symbols_l) or s in text or (args.fuzzy and s in text)):
                        continue
                pairs.append((p, data))

            if not pairs:
                print("No echoes found.")
                return 0

            def symbol_boost(d: dict) -> float:
                if not args.symbol:
                    return 0.0
                s = args.symbol.lower()
                tags_l = [str(ti).lower() for ti in (d.get("tags") or [])]
                meta = d.get("metadata") or {}
                symbols_l = [str(x).lower() for x in (meta.get("symbols") or [])]
                text = (str(d.get("title", "")) + "\n" + str(d.get("body", ""))).lower()
                if any(s in t for t in tags_l) or any(s in x for x in symbols_l):
                    return 0.25
                if args.fuzzy and s in text:
                    return 0.15
                return 0.0

            scored = [ (reson_score(d) + symbol_boost(d), p, d) for p, d in pairs ]
            if args.sort_by.lower() == "date":
                scored.sort(key=lambda x: get_date(x[2]), reverse=True)
            else:
                scored.sort(key=lambda x: x[0], reverse=True)
            top = scored[: max(1, int(limit))]

            # Dream-mode echo depth references
            ref_map = {}
            if dream_mode and echo_depth > 1:
                all_dream_pairs = [(p, d) for p, d in pairs if get_type(d) == 'dream']
                def _linked(ref: dict):
                    from datetime import datetime, timedelta
                    def _parse(dt: str):
                        try:
                            return datetime.fromisoformat(dt.replace('Z', '+00:00'))
                        except Exception:
                            return None
                    ts = _parse(str(ref.get('anchor_date') or ref.get('created_at') or ''))
                    tags_ref = set(str(t).lower() for t in (ref.get('tags') or []))
                    sym_ref = set(str(x).lower() for x in ((ref.get('metadata') or {}).get('symbols') or []))
                    links = []
                    for p, d in all_dream_pairs:
                        if d is ref:
                            continue
                        ok_date = False
                        if ts:
                            dt = _parse(str(d.get('anchor_date') or d.get('created_at') or ''))
                            if dt:
                                ok_date = abs((dt - ts).days) <= 3
                        tags_d = set(str(t).lower() for t in (d.get('tags') or []))
                        sym_d = set(str(x).lower() for x in ((d.get('metadata') or {}).get('symbols') or []))
                        ok_overlap = bool(tags_ref & tags_d or sym_ref & sym_d)
                        if ok_date or ok_overlap:
                            links.append(p.name)
                    return links[:10]
                for score, pth, dat in top:
                    ref_map[pth.name] = _linked(dat)

            def excerpt(text: str, length: int = 120) -> str:
                t = " ".join(text.split())
                return (t[: length - 1] + "…") if len(t) > length else t

            heading = "Codex Echo (Dream Mode)" if dream_mode else "# Codex Echo Results (" + ("Resonance" if args.sort_by.lower()=="resonance" else "Date") + " Sort)"
            lines = [heading]
            if args.phrase:
                lines.append(f"Matched: \"{args.phrase}\" | Fuzzy: {'Enabled' if args.fuzzy else 'Disabled'}" + (f" | Tone: {args.tone}" if args.tone else ""))
            elif args.tag or args.tone or args.typ or args.symbol or dream_mode:
                meta = []
                if args.tag: meta.append(f"Tag: {args.tag}")
                if args.tone: meta.append(f"Tone: {args.tone}")
                if args.typ: meta.append(f"Type: {args.typ}")
                if args.symbol: meta.append(f"Symbol: {args.symbol}")
                if dream_mode: meta.append("From: dream")
                lines.append("Filters: " + ", ".join(meta))
            lines.append("")

            idx = 1
            for score, path_i, data in top:
                label_type = get_type(data).capitalize()
                dt = get_date(data).split("T")[0]
                title = str(data.get("title") or path_i.stem)
                body = str(data.get("body") or "")
                tags_l = data.get("tags") or []
                mood = (data.get("metadata") or {}).get("mood")
                res_pct = int(round(min(1.0, score) * 100))
                lines.append(f"{idx}. {label_type}: {title}")
                if dt:
                    lines.append(f"   - Logged: {dt}")
                if tags_l:
                    lines.append(f"   - Tags: {', '.join(tags_l)}")
                if mood:
                    lines.append(f"   - Tone: {mood}")
                if args.sort_by.lower() == "resonance":
                    lines.append(f"   - Resonance: {res_pct}%")
                if body:
                    lines.append(f"   - Excerpt: \"{excerpt(body)}\"")
                if dream_mode and echo_depth > 1:
                    refs = ref_map.get(path_i.name) or []
                    if refs:
                        lines.append(f"   - Echo Depth: 1 → references [{', '.join(refs)}]")
                lines.append("")
                idx += 1

            lines.append("Use \"codex open <entry_id>\" to review.")
            print("\n".join(lines))
            return 0
        elif args.cmd == "list":
            try:
                from codex.core.indexer import list_entries  # type: ignore
            except Exception:
                print("[ERR] Indexer unavailable", file=sys.stderr)
                return 2
            rows = list_entries(Path(args.vault), tag=args.tag, date=args.date_str, typ=args.typ)
            if not rows:
                print("(no entries)")
                return 0
            for fname, it in rows:
                dt = (it.get("anchor_date") or it.get("created_at") or "").split("T")[0]
                title = it.get("title") or fname
                tags = ", ".join(it.get("tags") or [])
                print(f"- {dt:10s} [{it.get('type')}] {title}  (tags: {tags})  -> {fname}")
            return 0
        elif args.cmd == "index":
            try:
                from codex.core.indexer import build_index  # type: ignore
            except Exception:
                print("[ERR] Indexer unavailable", file=sys.stderr)
                return 2
            p = build_index(Path(args.vault))
            print(f"[OK] Rebuilt index at {p}")
            return 0
        elif args.cmd == "add":
            try:
                from codex.core.schema import validate_entry  # type: ignore
            except Exception:
                def validate_entry(_):
                    return True
            tags = [t.strip() for t in (args.tags_csv or "").split(",") if t.strip()]
            entry = {
                "title": args.title,
                "tags": tags,
                "created_at": args.date_str or "",
                "anchor_date": args.date_str or "",
                "body": args.body,
                "metadata": {"origin": "dream"} if args.dream else {},
            }
            if not validate_entry(entry):
                print("[ERR] Entry failed schema validation", file=sys.stderr)
                return 1
            vault_path = Path(args.vault)
            target_dir = vault_path / ("dreams" if args.dream else "entries")
            target_dir.mkdir(parents=True, exist_ok=True)
            import re
            date_part = (args.date_str or "undated").replace(":", "-")
            slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", args.title).strip("_") or "entry"
            out_path = target_dir / f"codex_{date_part}_{slug}.json"
            i = 1
            while out_path.exists():
                out_path = target_dir / f"codex_{date_part}_{slug}_{i}.json"
                i += 1
            out_path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
            try:
                from codex.core.indexer import build_index  # type: ignore
                build_index(vault_path)
            except Exception:
                pass
            print(f"[OK] Created {out_path}")
            return 0
        elif args.cmd == "update":
            import re
            from datetime import datetime, timezone
            vault_path = Path(args.vault)
            cfg = vault_path / "config.json"
            entries = vault_path / "entries"
            dreams = vault_path / "dreams"
            if not (cfg.exists() and entries.exists()):
                print("[ERR] Vault not found: expected config.json and entries/ in --vault path", file=sys.stderr)
                return 2
            files = list(entries.glob("*.json"))
            if dreams.exists():
                files += list(dreams.glob("*.json"))
            def matches_key(p: Path, data: dict) -> bool:
                if p.name == args.target or p.stem == args.target:
                    return True
                title = str(data.get("title", ""))
                if args.target == title:
                    return True
                tags = [str(t) for t in (data.get("tags") or [])]
                return args.target in tags
            candidates = []
            for p in files:
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if matches_key(p, data):
                    candidates.append((p, data))
            if not candidates:
                print(f"[ERR] No entry found matching: {args.target}", file=sys.stderr)
                return 1
            if len(candidates) > 1:
                names = ", ".join(p.name for p, _ in candidates[:10])
                print(f"[ERR] Multiple entries match '{args.target}'. Candidates: {names} ...", file=sys.stderr)
                return 2
            p, data = candidates[0]
            flags = re.MULTILINE | re.DOTALL
            total = 0
            if isinstance(data.get("title"), str):
                new_title, n = re.subn(args.pattern, args.replacement, data["title"], 0 if args.multiple else 1, flags=flags)
                if n:
                    data["title"] = new_title
                    total += n
            if isinstance(data.get("body"), str) and (args.multiple or total == 0):
                new_body, n = re.subn(args.pattern, args.replacement, data["body"], 0 if args.multiple else 1, flags=flags)
                if n:
                    data["body"] = new_body
                    total += n
            if total == 0:
                print("No changes applied (pattern not found).")
                return 0
            meta = data.get("metadata") or {}
            meta["last_updated"] = datetime.now(timezone.utc).isoformat()
            data["metadata"] = meta
            p.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"[OK] Updated {p.name} (replacements: {total})")
            return 0
        elif args.cmd == "export":
            # Prefer modular export engine if available
            try:
                from codex.core.export import run as export_run  # type: ignore
            except Exception:
                export_run = None  # type: ignore
            if export_run:
                rc = export_run(args.target, args.fmt, bool(args.with_metadata), args.output, Path(args.vault))
                return int(rc or 0)
            vault_path = Path(args.vault)
            entries = vault_path / "entries"
            dreams = vault_path / "dreams"
            exports = vault_path / "exports"
            cfg = vault_path / "config.json"
            if not (cfg.exists() and entries.exists()):
                print("[ERR] Vault not found: expected config.json and entries/ in --vault path", file=sys.stderr)
                return 2
            def collect_pairs():
                files = list(entries.glob("*.json"))
                if dreams.exists():
                    files.extend(dreams.glob("*.json"))
                pairs = []
                for p in files:
                    try:
                        data = json.loads(p.read_text(encoding="utf-8"))
                    except Exception:
                        continue
                    pairs.append((p, data))
                return pairs
            pairs = collect_pairs()
            def matches(p: Path, d: dict) -> bool:
                if args.target == "*":
                    return True
                if p.name == args.target or p.stem == args.target:
                    return True
                if str(d.get("title", "")) == args.target:
                    return True
                tags = [str(t) for t in (d.get("tags") or [])]
                return args.target in tags
            chosen = [(p, d) for p, d in pairs if matches(p, d)]
            if not chosen:
                print(f"[ERR] No entries matched: {args.target}", file=sys.stderr)
                return 1
            def redact(d: dict) -> dict:
                if args.with_metadata:
                    return d
                return {k: v for k, v in {"title": d.get("title"), "body": d.get("body")}.items() if v is not None}
            def render_single(d: dict, fmt_l: str) -> str:
                if fmt_l == "json":
                    return json.dumps(redact(d), indent=2)
                if fmt_l == "yaml":
                    try:
                        import yaml  # type: ignore
                        return yaml.safe_dump(redact(d), sort_keys=False)
                    except Exception:
                        return json.dumps(redact(d), indent=2)
                if fmt_l == "md":
                    title = d.get("title", "Untitled")
                    body = d.get("body", "") or ""
                    lines = [f"# {title}", "", body]
                    if args.with_metadata:
                        created = d.get("created_at", "")
                        tags = d.get("tags", []) or []
                        meta = d.get("metadata", {}) or {}
                        if created or tags:
                            lines.insert(2, f"- Created: {created}\n- Tags: {', '.join(tags)}\n")
                        if meta:
                            lines += ["", "## Metadata", "```json", json.dumps(meta, indent=2), "```"]
                    return "\n".join(lines).rstrip() + "\n"
                if fmt_l == "txt":
                    title = d.get("title", "Untitled")
                    body = d.get("body", "") or ""
                    return f"Title: {title}\n\n{body}\n"
                if fmt_l == "html":
                    import html as _html
                    title = _html.escape(str(d.get("title", "Untitled")))
                    body = _html.escape(str(d.get("body", "") or "")).replace("\n", "<br/>")
                    meta_block = ""
                    if args.with_metadata:
                        created = _html.escape(str(d.get("created_at", "")))
                        tags = ", ".join(_html.escape(str(x)) for x in (d.get("tags", []) or []))
                        meta = _html.escape(json.dumps(d.get("metadata", {}) or {}, indent=2))
                        meta_block = f"<p><em>Created:</em> {created} | <em>Tags:</em> {tags}</p><pre>{meta}</pre>"
                    return f"<html><head><meta charset='utf-8'><title>{title}</title></head><body><h1>{title}</h1>{meta_block}<p>{body}</p></body></html>\n"
                # pdf/rtf fallback use markdown
                title = d.get("title", "Untitled")
                body = d.get("body", "") or ""
                content = [f"# {title}", "", body]
                if args.with_metadata:
                    content += ["", "## Metadata", json.dumps(d.get("metadata", {}) or {}, indent=2)]
                return "\n".join(content) + "\n"
            fmt_l = (args.fmt or "md").lower()
            exports.mkdir(parents=True, exist_ok=True)
            ext_map = {"md": ".md", "txt": ".txt", "json": ".json", "yaml": ".yaml", "html": ".html", "pdf": ".pdf", "rtf": ".rtf"}
            if len(chosen) == 1 and args.target != "*":
                p, d = chosen[0]
                if args.output:
                    out_path = exports / args.output
                else:
                    datep = str(d.get("anchor_date") or d.get("created_at") or "").split("T")[0] or "undated"
                    label = "DreamEntry" if (d.get("metadata") or {}).get("origin", "").lower() == "dream" else "Entry"
                    fname = f"{label}__{''.join(c if c.isalnum() or c in ('-','_','.') else '_' for c in str(d.get('title') or p.stem))}__{''.join(c if c.isalnum() or c in ('-','_','.') else '_' for c in datep)}{ext_map.get(fmt_l, '.txt')}"
                    out_path = exports / fname
                rendered = render_single(d, fmt_l)
                out_path.write_text(rendered, encoding="utf-8")
                if fmt_l in ("pdf", "rtf"):
                    print(f"[OK] Wrote {fmt_l.upper()} content (markdown fallback) to {out_path}. Use pandoc for conversion if needed.")
                else:
                    print(f"[OK] Exported to {out_path}")
                return 0
            bundle = [redact(d) if fmt_l in ("json", "yaml") else d for _, d in chosen]
            if args.output:
                out_path = exports / args.output
            else:
                base = "CodexExport__all" if args.target == "*" else f"CodexExport__{''.join(c if c.isalnum() or c in ('-','_','.') else '_' for c in args.target)}"
                out_path = exports / f"{base}{ext_map.get(fmt_l, '.txt')}"
            if fmt_l == "json":
                out_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
            elif fmt_l == "yaml":
                try:
                    import yaml  # type: ignore
                    out_path.write_text(yaml.safe_dump(bundle, sort_keys=False), encoding="utf-8")
                except Exception:
                    out_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
            elif fmt_l == "html":
                parts = [render_single(d, "html") for d in bundle]
                out_path.write_text("\n".join(parts), encoding="utf-8")
            else:
                sep = "\n---\n\n"
                block_fmt = "md" if fmt_l in ("md", "pdf", "rtf") else ("txt" if fmt_l == "txt" else "md")
                parts = [render_single(d, block_fmt) for d in bundle]
                out_path.write_text(sep.join(parts), encoding="utf-8")
                if fmt_l in ("pdf", "rtf"):
                    print(f"[OK] Wrote {fmt_l.upper()} content (markdown fallback) to {out_path}. Use pandoc for conversion if needed.")
            print(f"[OK] Exported {len(chosen)} entries to {out_path}")
            return 0


    if __name__ == "__main__":
        sys.exit(main())
