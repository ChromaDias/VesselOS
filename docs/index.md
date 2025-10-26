---
layout: default
title: VesselOS – Landing
---

{% include nav.html %}

<div style="display:flex;flex-direction:column;gap:1rem;margin-top:1rem">
  <h1 style="margin:0">VesselOS</h1>
  <p style="font-size:1.15rem;max-width:60ch">
    Modular Codex architecture for memory, resonance search, and symbolic export. A CLI-first toolkit for dream logs, narrative fragments, and living knowledge bases.
  </p>
  <div style="display:flex;gap:.75rem;flex-wrap:wrap">
    <a class="btn" href="{{ site.baseurl }}/cli.html" style="padding:.6rem 1rem;background:#0366d6;color:#fff;border-radius:.4rem;text-decoration:none">Get Started</a>
    <a class="btn" href="{{ site.baseurl }}/architecture.html" style="padding:.6rem 1rem;border:1px solid #0366d6;color:#0366d6;border-radius:.4rem;text-decoration:none">Architecture</a>
    <a class="btn" href="https://github.com/ChromaDias/VesselOS/releases/latest" style="padding:.6rem 1rem;border:1px solid #555;color:#555;border-radius:.4rem;text-decoration:none">Download</a>
    <a class="btn" href="https://github.com/ChromaDias/VesselOS" style="padding:.6rem 1rem;border:1px solid #555;color:#555;border-radius:.4rem;text-decoration:none">GitHub</a>
  </div>
</div>

## Highlights

- CLI-first commands: `init`, `add`, `list`, `summon`, `echo`, `grep`, `update`, `export`, `snapshot`
- Dream-aware retrieval with symbolic filters and resonance search
- Structured exports (md/txt/json/yaml/html) + release bundles via CI
- Snapshots with tag/date/type filters and optional ZIP packaging

## Architecture Preview

```
User / Chroma ─▶ CLI (codex) ─▶ Command Engine ─▶ Core (store/query/render)
                                    │                   │
                                    │                   ├─ Indexer (system/index.json)
                                    │                   ├─ Export (md/txt/json/yaml/html)
                                    │                   └─ Snapshot (system/snapshots/*)
                                    │
                                    └─ Wizards (export wizard)

Vault
  • entries/ • dreams/ • exports/ • system/index.json • system/snapshots/
```

See the full map on the [Architecture]({{ site.baseurl }}/architecture.html) page.

## Quick Start

```bash
# 1) Clone
git clone https://github.com/ChromaDias/VesselOS.git
cd VesselOS

# 2) Initialize a vault
./scripts/codex init --name vessel_relics --base VesselOS/codex

# 3) Add an entry
./scripts/codex add --title "First Entry" --body "Hello Vessel." --tags "log" --date 2025-10-25 --vault VesselOS/codex/vessel_relics

# 4) Explore
./scripts/codex list --vault VesselOS/codex/vessel_relics
./scripts/codex grep --phrase Vessel --vault VesselOS/codex/vessel_relics
```

## Learn More

- Read the full CLI guide: [CLI Reference]({{ site.baseurl }}/cli.html)
- Explore design: [Architecture]({{ site.baseurl }}/architecture.html)
