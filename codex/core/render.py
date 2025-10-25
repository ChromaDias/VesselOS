from __future__ import annotations

import json
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore


def _redact_obj(d: dict, with_meta: bool) -> dict:
    if with_meta:
        return d
    return {k: d.get(k) for k in ("title", "body") if d.get(k) is not None}


def render_single(d: dict, fmt: str, with_metadata: bool) -> str:
    fmt_l = (fmt or "md").lower()
    if fmt_l == "json":
        return json.dumps(_redact_obj(d, with_metadata), indent=2)
    if fmt_l == "yaml":
        obj = _redact_obj(d, with_metadata)
        if yaml is None:
            return json.dumps(obj, indent=2)
        return yaml.safe_dump(obj, sort_keys=False)
    if fmt_l == "html":
        import html as _html
        title = _html.escape(str(d.get("title", "Untitled")))
        body = _html.escape(str(d.get("body", "") or "")).replace("\n", "<br/>")
        meta_block = ""
        if with_metadata:
            created = _html.escape(str(d.get("created_at", "")))
            tags = ", ".join(_html.escape(str(x)) for x in (d.get("tags", []) or []))
            meta = _html.escape(json.dumps(d.get("metadata", {}) or {}, indent=2))
            meta_block = f"<p><em>Created:</em> {created} | <em>Tags:</em> {tags}</p><pre>{meta}</pre>"
        return f"<html><head><meta charset='utf-8'><title>{title}</title></head><body><h1>{title}</h1>{meta_block}<p>{body}</p></body></html>\n"

    title = d.get("title", "Untitled")
    body = d.get("body", "") or ""
    if fmt_l == "txt":
        return f"Title: {title}\n\n{body}\n"
    # markdown (default)
    lines = [f"# {title}", ""]
    if with_metadata:
        created = d.get("created_at", "")
        tags = d.get("tags", []) or []
        if created or tags:
            lines.append(f"- Created: {created}\n- Tags: {', '.join(tags)}\n")
    lines.append(body)
    if with_metadata:
        meta = d.get("metadata", {}) or {}
        if meta:
            lines += ["", "## Metadata", "```json", json.dumps(meta, indent=2), "```"]
    return "\n".join(lines).rstrip() + "\n"


EXT_MAP = {
    "md": ".md",
    "txt": ".txt",
    "json": ".json",
    "yaml": ".yaml",
    "html": ".html",
    "pdf": ".pdf",
    "rtf": ".rtf",
}

