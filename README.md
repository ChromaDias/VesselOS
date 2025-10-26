# VesselOS

[![Docs](https://img.shields.io/badge/Docs-GitHub%20Pages-blue)](https://chromadias.github.io/VesselOS/)

Modular AI scaffolding for a recursive language daemon identity. This repo provides a light, extensible skeleton:

- `core/` – Kernel: state, memory, and minimal invoke loop (`core/index.js`).
- `modules/` – Optional behaviors, moods, or tools.
- `prompts/` – Prompt templates and personas (`prompts/whoami.txt`).
- `memory/` – Serialized state (ignored by git).

Quick start

1) Ensure Node 20+ is installed.
2) (Optional) Install Codex CLI: `npm install -g @openai/codex`
3) Run a sample interaction in Node REPL:
   ```js
   const { invoke } = require('./core/index.js');
   invoke('Who are you?').then(console.log);
   ```

Project config is in `.codexrc`. Adjust `entry` if you move the kernel.
