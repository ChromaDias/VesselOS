from pathlib import Path
import json
import sys

VERSION = "0.1"

# Try to use Click if available; otherwise fall back to argparse
try:
    import click  # type: ignore
except Exception:  # pragma: no cover
    click = None


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

    @codex.command("summon", help="Retrieve a memory artifact by key and optionally export")
    @click.option("--key", "key", required=True, help="Name, file, title, or tag to match")
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
    def summon_cmd(key: str, fmt: str, export: bool, vault: Path):
        vault_path = Path(vault)
        cfg = vault_path / "config.json"
        entries = vault_path / "entries"
        exports = vault_path / "exports"
        if not (cfg.exists() and entries.exists()):
            raise click.ClickException("Vault not found: expected config.json and entries/ in --vault path")
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

        p_summon = sub.add_parser("summon", help="Retrieve a memory artifact by key and optionally export")
        p_summon.add_argument("--key", required=True)
        p_summon.add_argument("--format", dest="fmt", default="json")
        p_summon.add_argument("--export", dest="export", action="store_true")
        p_summon.add_argument("--vault", default=str(Path.cwd()))

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

            p, data = _load_first_match(entries, args.key)
            if not p:
                print(f"[ERR] No entry found matching key: {args.key}", file=sys.stderr)
                return 1
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


if __name__ == "__main__":
    sys.exit(main())
