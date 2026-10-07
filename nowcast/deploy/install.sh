#!/usr/bin/env bash
# Install BTC 5m Up/Down Nowcast (G1) on a fresh Ubuntu/Debian VPS.
# Usage:  bash install.sh
# Re-run safe. Creates ./venv, installs deps, prepares data/ dirs.
set -euo pipefail

echo "==> [1/4] system packages (python3, venv, tmux)"
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-venv python3-pip tmux curl > /dev/null
python3 --version

echo "==> [2/4] virtualenv + deps"
if [ ! -d venv ]; then python3 -m venv venv; fi
./venv/bin/pip install -q --upgrade pip
./venv/bin/pip install -q -r nowcast/requirements.txt

echo "==> [3/4] directories + .env"
mkdir -p data/raw data/gamma data/reports
touch data/raw/.gitkeep data/gamma/.gitkeep data/reports/.gitkeep
if [ ! -f .env ]; then
  cp nowcast/.env.example .env
  chmod 600 .env
  echo "    .env dibuat dari contoh (chmod 600). ISI kredensial CLOB dulu sebelum merekam."
else
  echo "    .env sudah ada, tidak ditimpa."
fi

echo "==> [4/4] smoke test (tanpa kredensial)"
./venv/bin/python -m pytest nowcast/tests -q 2>&1 | tail -2
./venv/bin/python -m nowcast.ingest.polybolt_ws --dry-run --duration-sec 10 --out /tmp/smoke-raw > /dev/null
echo "    smoke test OK."

echo ""
echo "SELESAI. Langkah berikut:"
echo "  1. nano .env   # isi POLY_CLOB_API_KEY/SECRET/PASSPHRASE"
echo "  2. ./venv/bin/python -m nowcast.ingest.gamma --slug btc-updown-5m-<epoch> --out data/gamma"
echo "  3. bash nowcast/deploy/run-record.sh 48   # rekam 48 jam dalam tmux"
