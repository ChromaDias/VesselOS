// VesselOS core entrypoint
// Purpose: minimal kernel exposing state, memory hooks, and a simple invoke() loop.

const fs = require('fs');
const path = require('path');

const memoryDir = path.resolve(__dirname, '..', 'memory');

function ensureMemoryDir() {
  if (!fs.existsSync(memoryDir)) fs.mkdirSync(memoryDir, { recursive: true });
}

function loadMem(filename = 'session.json') {
  ensureMemoryDir();
  const p = path.join(memoryDir, filename);
  if (!fs.existsSync(p)) return { notes: [] };
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

function saveMem(state, filename = 'session.json') {
  ensureMemoryDir();
  const p = path.join(memoryDir, filename);
  fs.writeFileSync(p, JSON.stringify(state, null, 2));
}

async function invoke(input, state = loadMem()) {
  const note = { t: new Date().toISOString(), input };
  state.notes.push(note);
  saveMem(state);
  return {
    reply: `Vessel received: ${input}`,
    state,
  };
}

module.exports = { invoke, loadMem, saveMem };

