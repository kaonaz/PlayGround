#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
/usr/bin/time -p pwd
PROJECT_ROOT="$(pwd)"
PORT="${PORT:-3000}"
DIST_DIR="$PROJECT_ROOT/dist"
export DIST_DIR PORT
WEB_DIR="${OPENCODE_WEB_DIR:-/home/runner/work/_temp/omgithub-web}"
/usr/bin/time -p mkdir -p "$WEB_DIR"
/usr/bin/time -p test -f "$DIST_DIR/index.html"
if /usr/bin/time -p test -f "$PROJECT_ROOT/package.json"; then
  if /usr/bin/time -p test -f "$PROJECT_ROOT/package-lock.json"; then
    /usr/bin/time -p npm ci --no-audit --no-fund
  else
    /usr/bin/time -p npm install --no-audit --no-fund
  fi
  if /usr/bin/time -p node -e "process.exit(require('./package.json').scripts?.build?0:1)"; then
    /usr/bin/time -p npm run build
  fi
  /usr/bin/time -p test -f "$DIST_DIR/index.html"
fi
/usr/bin/time -p node -e 'const fs=require("fs");const p=JSON.parse(fs.readFileSync(0,"utf8"));fs.writeFileSync(process.argv[1],JSON.stringify(p));' "$WEB_DIR/deployment-output.json" <<EOF
{"project": "$PROJECT_ROOT", "directory": "$DIST_DIR"}
EOF
/usr/bin/time -p cat "$WEB_DIR/deployment-output.json"
/usr/bin/time -p node --input-type=module -e '
import { createServer } from "node:http";
import { readFileSync, statSync, existsSync } from "node:fs";
import { resolve, join, extname } from "node:path";
const root = process.env.DIST_DIR;
const port = Number(process.env.PORT || "3000");
const mime = { ".html":"text/html", ".js":"application/javascript", ".css":"text/css", ".json":"application/json", ".svg":"image/svg+xml", ".png":"image/png", ".jpg":"image/jpeg", ".webp":"image/webp", ".wasm":"application/wasm", ".glb":"model/gltf-binary" };
const server = createServer((req, res) => {
  try {
    const url = new URL(req.url, "http://localhost");
    let path = resolve(root, "." + decodeURIComponent(url.pathname));
    if (path !== resolve(root) && !path.startsWith(resolve(root) + "/")) { res.writeHead(404); res.end(); return; }
    try { if (statSync(path).isDirectory()) path = join(path, "index.html"); } catch { path = join(root, "index.html"); }
    if (!existsSync(path)) path = join(root, "index.html");
    res.setHeader("Content-Type", mime[extname(path)] || "application/octet-stream");
    res.setHeader("Cache-Control", "no-cache");
    res.end(readFileSync(path));
  } catch { res.writeHead(404); res.end("Not found"); }
});
server.listen(port, "0.0.0.0", () => console.log(`Serving ${root} on ${port}`));
'
