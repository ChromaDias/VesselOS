---
layout: default
title: CLI Command Reference
---

{% include nav.html %}

# CLI Command Reference

Below are the core codex commands and common options.

## init
- Scaffold a new vault under the base path.
- Example: `codex init --name vessel_relics --base VesselOS/codex`

## add
- Create a new entry (optionally dream-origin).
- Example: `codex add --title "Null Tracking" --body "Ping" --tags "thread,log" --date 2025-10-25`

## list
- List entries with filters.
- Options: `--tag <t>` `--date <YYYY-MM-DD>` `--type dream|log|fragment|event|entry`
- Example: `codex list --tag thread`

## summon
- Retrieve entries by key or dream filters; render to md/txt/json/yaml; export to file.
- Key flow: `codex summon --key anima --format md --export`
- Dream flow: `codex summon --dream --tag anima --tone calm --format md --export`

## echo
- Resonance search (phrase/tag/tone/type) with fuzzy ranking.
- Examples:
  - `codex echo --phrase "silenced lighthouse" --fuzzy --limit 5`
  - `codex echo --from dream --symbol water --feeling mystic --limit 5`

## grep
- Regex/phrase search with optional JSON output.
- Options: `--pattern <re>` `--phrase <text>` `--ignore-case` `--field title|body|any` `--json` `--fields title,body`
- Examples:
  - `codex grep --phrase stair --json --fields title,body`
  - `codex grep --pattern "dream|vision" --ignore-case --limit 50`

## update
- Surgical regex replacement in title/body.
- Example: `codex update anima --pattern "staircase" --replacement "stairwell" --multiple`

## export
- Export single entries or sets to md/txt/json/yaml/html (pdf/rtf as md fallback).
- Examples:
  - `codex export anima --format md --with-metadata`
  - `codex export "*" --format json --output FullCodexArchive.json`

## snapshot
- Point-in-time copies of entries; supports filters and zip bundling.
- Options: `--all` `--tag` `--date` `--type` `--zip` `--zip-out`
- Examples:
  - `codex snapshot --all --type dream --zip`
  - `codex snapshot anima --zip`

## paths
- Vault layout: `entries/` `dreams/` `exports/` `system/index.json` `system/snapshots/`
- Core files: `codex/core/*` `codex/config.yaml`

