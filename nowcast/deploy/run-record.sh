#!/usr/bin/env bash
# Record PolyBolt TWAP+spot inside a persistent tmux session.
# Usage:  bash nowcast/deploy/run-record.sh [hours]   (default 48)
# Attach: tmux attach -t nowcast-g1   | Detach: Ctrl-b lalu d
set -euo pipefail
HOURS="${1:-48}"
SECS=$(( HOURS * 3600 ))
SESS="nowcast-g1"

if [ ! -f .env ]; then echo "ERROR: .env belum ada. Jalankan bash install.sh dulu."; exit 1; fi
# shellcheck disable=SC1091
set -a; source .env; set +a
if [ -z "${POLY_CLOB_API_KEY:-}" ]; then echo "ERROR: POLY_CLOB_API_KEY kosong di .env"; exit 1; fi

tmux kill-session -t "$SESS" 2>/dev/null || true
tmux new-session -d -s "$SESS" \
  "./venv/bin/python -m nowcast.ingest.polybolt_ws --duration-sec $SECS --out data/raw 2>&1 | tee data/raw/record-$(date -u +%Y%m%dT%H%M%S).log"
echo "Merekam $HOURS jam di tmux session '$SESS'."
echo "  pantau : tmux attach -t $SESS"
echo "  selesai: python -m nowcast.eval.g1_match --raw data/raw --gamma data/gamma --out data/reports"
