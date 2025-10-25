from pathlib import Path
import json


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    output_dir = repo_root / "codex"
    output_dir.mkdir(parents=True, exist_ok=True)

    codex_config = {
        "version": "0.1",
        "author": "Chroma",
        "project": "VesselOS",
        "entry_point": "index.md",
        "structure": {
            "memory": "layered-tagged",
            "logs": "timestamped-markdown",
            "modes": ["Archivist", "Guardian", "Threadweaver"],
            "defaults": {"active_mode": "Guardian", "render": "plaintext+symbolic"},
        },
        "recall": {
            "method": "contextual-lookup",
            "pattern_matching": True,
            "fallback": "Echo",
        },
        "integration": {
            "environment": "CLI-first",
            "dependencies": ["python3.11+", "rich", "typer"],
            "export_formats": ["json", "md", "txt"],
        },
    }

    output_file = output_dir / "config.json"
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(codex_config, f, indent=2)

    print(f"Wrote {output_file}")


if __name__ == "__main__":
    main()

