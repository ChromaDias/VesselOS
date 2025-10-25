from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore


DEFAULTS = {
    "output_dir": "exports",
    "date_format": "%Y-%m-%d",
    "include_metadata_default": False,
}


def load_config(repo_root: Path | None = None) -> Dict[str, Any]:
    repo_root = repo_root or Path.cwd()
    cfg_path = repo_root / "VesselOS" / "codex" / "config.yaml"
    if not cfg_path.exists() or yaml is None:
        return dict(DEFAULTS)
    try:
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        out = dict(DEFAULTS)
        out.update({k: v for k, v in (data or {}).items() if v is not None})
        return out
    except Exception:
        return dict(DEFAULTS)

