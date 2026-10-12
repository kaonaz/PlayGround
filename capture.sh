#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")"
/usr/bin/time -p pwd
RUNTIME_FALLBACK="/home/runner/work/_temp/omgithub-runtime"
RUNTIME_DIR="${RUNTIME_DIR:-$RUNTIME_FALLBACK}"
if [[ -z "${CAPTURE_URL:-}" ]]; then
  echo "CAPTURE_URL is required." >&2
  exit 1
fi
if [[ -z "${CAPTURE_DIR:-}" ]]; then
  echo "CAPTURE_DIR is required." >&2
  exit 1
fi
/usr/bin/time -p mkdir -p "$CAPTURE_DIR"
/usr/bin/time -p test -n "$CAPTURE_URL"
/usr/bin/time -p test -d "$CAPTURE_DIR"
/usr/bin/time -p node --version
set +e
/usr/bin/time -p node "$RUNTIME_DIR/scripts/default-capture.mjs"
status=$?
set -u
if [[ $status -ne 0 ]]; then
  echo "capture backend exited $status" >&2
  exit $status
fi
/usr/bin/time -p test -f "$CAPTURE_DIR/final-desktop.png"
/usr/bin/time -p test -f "$CAPTURE_DIR/final-mobile.png"
/usr/bin/time -p test -s "$CAPTURE_DIR/final-desktop.png"
/usr/bin/time -p test -s "$CAPTURE_DIR/final-mobile.png"
/usr/bin/time -p ls -l "$CAPTURE_DIR/final-desktop.png" "$CAPTURE_DIR/final-mobile.png"
