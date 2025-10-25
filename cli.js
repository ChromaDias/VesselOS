#!/usr/bin/env node
// VesselOS CLI Wrapper
// Usage:
//   node cli.js "your message" [-c '{"key":"value"}'] [-f context.json]
//   echo "streamed input" | node cli.js [-c '{"k":"v"}']

const fs = require("fs");
const path = require("path");
const { respond } = require("./core/index.js");

function parseArgs(argv) {
  const out = { message: null, context: {} };
  const rest = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "-h" || a === "--help") {
      out.help = true;
      continue;
    }
    if (a === "-c" || a === "--context") {
      const v = argv[i + 1];
      i++;
      if (v) {
        try { out.context = JSON.parse(v); } catch { console.error("Invalid JSON for --context"); process.exit(2); }
      }
      continue;
    }
    if (a === "-f" || a === "--context-file") {
      const p = argv[i + 1];
      i++;
      if (!p) { console.error("--context-file requires a path"); process.exit(2); }
      try {
        const raw = fs.readFileSync(path.resolve(p), "utf8");
        out.context = JSON.parse(raw);
      } catch (e) {
        console.error(`Failed to read context file: ${e.message}`);
        process.exit(2);
      }
      continue;
    }
    rest.push(a);
  }
  if (rest.length) out.message = rest.join(" ");
  return out;
}

function usage() {
  console.log(`VesselOS CLI\n\nUsage:\n  node cli.js "message" [-c '{"k":"v"}'] [-f context.json]\n  echo "message" | node cli.js [-c '{"k":"v"}']\n`);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) { usage(); return; }

  const run = (msg) => {
    if (!msg) { usage(); process.exit(1); }
    const out = respond(msg, args.context || {});
    console.log(out);
  };

  if (args.message) {
    run(args.message);
    return;
  }

  if (!process.stdin.isTTY) {
    let buf = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (c) => buf += c);
    process.stdin.on("end", () => run(buf.trim()));
  } else {
    usage();
    process.exit(1);
  }
}

main();

