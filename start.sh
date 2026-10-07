#!/usr/bin/env bash
# Serve the built static dashboard (dist/) in the foreground on PORT (default 3000).
# Writes worker metadata (deployment-output.json) to OPENCODE_WEB_DIR only;
# source and built output stay inside PROJECT_DIR.
set -euo pipefail
cd "$(dirname "$0")"
/usr/bin/time -p pwd
/usr/bin/time -p node --version
/usr/bin/time -p test -f dist/index.html
PROJECT_DIR="$(/usr/bin/time -p pwd)"
DIST_DIR="$PROJECT_DIR/dist"
WEB_DIR="${OPENCODE_WEB_DIR:-/home/runner/work/_temp/omgithub-web}"
/usr/bin/time -p mkdir -p "$WEB_DIR"
/usr/bin/time -p node -e 'const fs=require("fs");fs.writeFileSync(process.argv[1],JSON.stringify({project:process.argv[2],directory:process.argv[3]}))' "$WEB_DIR/deployment-output.json" "$PROJECT_DIR" "$DIST_DIR"
/usr/bin/time -p cat "$WEB_DIR/deployment-output.json"
PORT="${PORT:-3000}"
export PORT
exec node scripts/serve-static.mjs "$DIST_DIR"
