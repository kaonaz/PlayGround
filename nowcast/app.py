"""Minimal G1 status app (read-only, NO trading).

Serves gate status + latest G1 report so this qualifies as an inspectable
"App" while staying inside G1 scope (measurement only, no orders, no signals).

Run: uvicorn nowcast.app:app --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import glob
import json
import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

REPORTS = os.environ.get("REPORTS_DIR", "data/reports")
CONFIG_PATH = os.environ.get("CONFIG_PATH", "nowcast/config.yaml")

app = FastAPI(title="BTC 5m Up/Down Nowcast — G1 (no trading)")


def latest_report() -> dict | None:
    paths = sorted(glob.glob(os.path.join(REPORTS, "g1_match-*.json")))
    if not paths:
        return None
    try:
        return {"path": paths[-1], "report": json.load(open(paths[-1]))}
    except Exception as e:
        return {"path": paths[-1], "error": str(e)}


@app.get("/health")
def health():
    return {"ok": True, "gate": "G1", "trading_enabled": False}


@app.get("/g1/status")
def g1_status():
    lat = latest_report()
    if lat is None:
        return {"gate": "G1", "status": "NO_REPORT_YET",
                "next": "record 1h -> fetch gamma -> run g1_match (see nowcast/README.md)"}
    rep = lat.get("report", {})
    return {"gate": "G1", "status": rep.get("verdict", "UNKNOWN"),
            "per_rule": rep.get("per_rule"), "perfect_rules": rep.get("perfect_rules"),
            "report_path": lat.get("path")}


@app.get("/", response_class=HTMLResponse)
def index():
    lat = latest_report()
    body = json.dumps((lat or {}).get("report", lat or {"status": "NO_REPORT_YET"}), indent=2)[:4000]
    return f"""<html><head><title>BTC 5m Nowcast — G1</title></head>
<body style="background:#0b0e11;color:#e6edf3;font-family:monospace;padding:24px">
<h2>BTC 5m Up/Down Nowcast — G1 (measurement only, NO trading)</h2>
<p>Gate: G1 data match &middot; Trading: <b>disabled</b> &middot; <a href="/g1/status">/g1/status</a> &middot; <a href="/health">/health</a></p>
<pre>{body}</pre>
<p>Run: <code>python -m nowcast.run.live --step record --duration-sec 3600</code> then gamma + match. See nowcast/README.md</p>
</body></html>"""
