# BTC 5m Up/Down Nowcast Engine — G1 slice (v2.3)

Research + measurement only. **No order execution.** G2–G5 code paths are gated stubs.

## Quickstart (G1 order: record → gamma → match)

```bash
pip install -r nowcast/requirements.txt
cp nowcast/.env.example .env   # fill CLOB creds (never commit)

# 1. Record 1h of official TWAP + spot (then extend to ~48h / 576 windows)
python -m nowcast.run.live --step record --duration-sec 3600
# no-creds smoke test:
python -m nowcast.run.live --step record --duration-sec 20 --dry-run

# 2. Fetch 1–2 RESOLVED markets (rule text, startDate/endDate, outcome)
python -m nowcast.ingest.gamma --slug btc-updown-5m-<epoch> --out data/gamma

# 3. Score the 3 boundary rules separately (H1a)
python -m nowcast.eval.g1_match --raw data/raw --gamma data/gamma --out data/reports
```

Or step-by-step directly:

```bash
python -m nowcast.ingest.polybolt_ws --duration-sec 3600 --out data/raw
python -m nowcast.ingest.gamma --slug btc-updown-5m-<epoch> --out data/gamma
python -m nowcast.eval.g1_match --raw data/raw --gamma data/gamma --out data/reports
```

## Tests

```bash
pytest nowcast/tests -q
```

## Status app (read-only)

```bash
uvicorn nowcast.app:app --host 127.0.0.1 --port 8000
# GET /health  /g1/status  /
```

## Gate rule

- `run/backtest.py` exits(2) until a `data/reports/g1_match-*.json` with `verdict == PASS` exists.
- Hypotheses live in `nowcast/config.yaml` — write them BEFORE recording.
- Credentials only via env (`POLY_CLOB_API_KEY/SECRET/PASSPHRASE`), never in repo/logs.
- TWAP stored verbatim; spot is a feature; `source` re-read every message + reconnect.
