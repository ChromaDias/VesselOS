// VesselOS Codex Core Entry Point
// core/index.js


const fs = require("fs");
const path = require("path");


const memoryPath = path.join(__dirname, "../memory");

function ensureMemoryDir() {
  if (!fs.existsSync(memoryPath)) {
    fs.mkdirSync(memoryPath, { recursive: true });
  }
}


function loadMemory(id) {
const file = path.join(memoryPath, `${id}.json`);
if (!fs.existsSync(file)) return null;
return JSON.parse(fs.readFileSync(file, "utf-8"));
}


function saveMemory(id, data) {
  ensureMemoryDir();
  const file = path.join(memoryPath, `${id}.json`);
  fs.writeFileSync(file, JSON.stringify(data, null, 2));
}


function respond(input, context = {}) {
  // Placeholder logic for identity-synced output
  const store = loadMemory("vessel");
  const event = { input, context, timestamp: new Date().toISOString() };

  let nextStore;
  if (!store) {
    nextStore = { events: [event] };
  } else if (Array.isArray(store)) {
    // Legacy array format
    store.push(event);
    nextStore = store;
  } else {
    if (!Array.isArray(store.events)) store.events = [];
    store.events.push(event);
    if (store.meta) store.meta.last_updated = new Date().toISOString();
    nextStore = store;
  }

  saveMemory("vessel", nextStore);

  // Future: prompt generation + Codex integration here
  return `Vessel heard: "${input}" and remembered it.`;
}


module.exports = {
respond
};
