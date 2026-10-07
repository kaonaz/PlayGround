"""PolyBolt WS recorder — G1 step 1 (spec sections VI/VII/VIII).

Records official TWAP (label) + spot (feature) verbatim to Parquet.

Protocol (docs.polymarket.com/api-reference/live-data/overview, 2026-10-06):
  url: wss://ws-live-v2.polymarket.com/ws
  auth:        {"op":"auth","rid":"a1","auth":{"apiKey","secret","passphrase"}}
  subscribe:   {"op":"subscribe","rid":"s1","subscriptions":[{channel,filter}...]}
  envelope:    {"v","channel","seq","ts","snapshot?","dropped?","payload":{...}}
  live payload:    {symbol, value, full_accuracy_value, timestamp, source}
  snapshot payload:{symbol, source, data:[{timestamp,value,full_accuracy_value}...]}
  seq is per-connection AND per-channel, resets on reconnect.
  server WS ping every 25s; app-level {"op":"ping"} -> {"op":"pong"}.

Usage:
  python -m nowcast.ingest.polybolt_ws --duration-sec 3600 --out data/raw
  python -m nowcast.ingest.polybolt_ws --dry-run --duration-sec 20 --out data/raw  # no creds needed
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import time
import uuid

from ..store.parquet_writer import RawParquetWriter

WS_URL = os.environ.get("POLY_WS_URL", "wss://ws-live-v2.polymarket.com/ws")

SUBSCRIPTIONS = [
    {"channel": "price.crypto.twap", "filter": {"symbol": "btcusd", "window_seconds": 60}},
    {"channel": "price.crypto", "filter": {"symbol": "btcusd"}},
]


def _creds() -> tuple[str, str, str]:
    return (
        os.environ.get("POLY_CLOB_API_KEY", ""),
        os.environ.get("POLY_CLOB_API_SECRET", ""),
        os.environ.get("POLY_CLOB_PASSPHRASE", ""),
    )


def envelope_to_rows(env: dict, *, connection_id: str) -> list[dict]:
    """Expand one envelope into 1..N raw-store rows (snapshots expand per point)."""
    recv_mono_ns = time.monotonic_ns()
    recv_wall_ms = int(time.time() * 1000)
    channel = str(env.get("channel", ""))
    seq = env.get("seq")
    ts_ms = env.get("ts")
    is_snapshot = bool(env.get("snapshot", False))
    dropped = env.get("dropped", 0) or 0
    payload = env.get("payload", {}) or {}
    raw = json.dumps(env, separators=(",", ":"))

    rows: list[dict] = []
    if is_snapshot:
        data = payload.get("data", []) or []
        symbol = str(payload.get("symbol", ""))
        source = str(payload.get("source", ""))
        window = 60 if channel == "price.crypto.twap" else None
        for pt in data:
            rows.append(
                {
                    "recv_mono_ns": recv_mono_ns,
                    "recv_wall_ms": recv_wall_ms,
                    "channel": channel,
                    "symbol": symbol,
                    "source": source,
                    "seq": int(seq) if seq is not None else None,
                    "ts_ms": int(ts_ms) if ts_ms is not None else None,
                    "payload_ts_ms": int(pt.get("timestamp")) if pt.get("timestamp") is not None else None,
                    "value_str": str(pt.get("value")) if pt.get("value") is not None else None,
                    "full_accuracy_value": str(pt.get("full_accuracy_value") or ""),
                    "window_seconds": window,
                    "is_snapshot": True,
                    "dropped": int(dropped),
                    "raw_json": raw,
                    "connection_id": connection_id,
                }
            )
    else:
        rows.append(
            {
                "recv_mono_ns": recv_mono_ns,
                "recv_wall_ms": recv_wall_ms,
                "channel": channel,
                "symbol": str(payload.get("symbol", "")),
                "source": str(payload.get("source", "")),
                "seq": int(seq) if seq is not None else None,
                "ts_ms": int(ts_ms) if ts_ms is not None else None,
                "payload_ts_ms": int(payload.get("timestamp")) if payload.get("timestamp") is not None else None,
                "value_str": str(payload.get("value")) if payload.get("value") is not None else None,
                "full_accuracy_value": str(payload.get("full_accuracy_value") or ""),
                "window_seconds": 60 if channel == "price.crypto.twap" else None,
                "is_snapshot": False,
                "dropped": int(dropped),
                "raw_json": raw,
                "connection_id": connection_id,
            }
        )
    return rows


async def _record_once(duration_sec: float, out_dir: str) -> dict:
    import websockets

    api_key, secret, passphrase = _creds()
    if not (api_key and secret and passphrase):
        raise SystemExit(
            "Missing CLOB credentials. Set POLY_CLOB_API_KEY / POLY_CLOB_API_SECRET / "
            "POLY_CLOB_PASSPHRASE (see nowcast/.env.example). "
            "Never put credentials in the repo or logs. "
            "Tip: use --dry-run to test without credentials."
        )
    connection_id = uuid.uuid4().hex[:12]
    stats = {"n_rows": 0, "n_env": 0, "n_snapshot": 0, "dropped_total": 0, "reconnects": 0}
    deadline = time.time() + duration_sec
    writer = RawParquetWriter(out_dir)
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=20, max_size=2 * 1024 * 1024) as ws:
                # 1. auth (max 8 frames/connection — we send exactly one)
                await ws.send(json.dumps({"op": "auth", "rid": "a1", "auth": {"apiKey": api_key, "secret": secret, "passphrase": passphrase}}))
                authed = False
                # 2. subscribe after authed (also proactively send; server enforces order)
                await ws.send(json.dumps({"op": "subscribe", "rid": "s1", "subscriptions": SUBSCRIPTIONS}))
                async for raw in ws:
                    if time.time() >= deadline:
                        break
                    try:
                        env = json.loads(raw)
                    except json.JSONDecodeError:
                        print(f"[ws] non-JSON frame ({len(raw)} bytes), ignored", flush=True)
                        continue
                    op = env.get("op")
                    if op == "authed":
                        authed = True
                        print("[ws] authed ok", flush=True)
                        continue
                    if op in ("subscribed", "unsubscribed", "pong"):
                        print(f"[ws] ack: {raw[:300]}", flush=True)
                        continue
                    if op == "error":
                        print(f"[ws] server error: {raw[:500]}", flush=True)
                        continue
                    if "channel" not in env:
                        print(f"[ws] unknown frame: {raw[:300]}", flush=True)
                        continue
                    rows = envelope_to_rows(env, connection_id=connection_id)
                    for r in rows:
                        writer.append(r)
                    stats["n_env"] += 1
                    stats["n_rows"] += len(rows)
                    if env.get("snapshot"):
                        stats["n_snapshot"] += 1
                    stats["dropped_total"] += int(env.get("dropped", 0) or 0)
                    if stats["n_env"] % 50 == 0:
                        print(f"[ws] env={stats['n_env']} rows={stats['n_rows']} snapshot={stats['n_snapshot']} dropped={stats['dropped_total']}", flush=True)
                break  # deadline reached inside loop
        except Exception as e:  # reconnect with backoff (4002/1006 style)
            stats["reconnects"] += 1
            wait = min(30.0, 1.0 * (2 ** min(attempt, 5))) + random.random()
            print(f"[ws] disconnect ({type(e).__name__}: {e}); reconnect in {wait:.1f}s (attempt {attempt})", flush=True)
            if time.time() + wait >= deadline:
                break
            await asyncio.sleep(wait)
            connection_id = uuid.uuid4().hex[:12]  # seq resets on reconnect -> new connection_id
    writer.flush()
    stats["authed_hint"] = True
    return stats


async def _dry_run(duration_sec: float, out_dir: str) -> dict:
    """Synthetic 1-sec TWAP + spot ticks so matcher/tests run without credentials."""
    import math

    writer = RawParquetWriter(out_dir)
    connection_id = "dryrun-" + uuid.uuid4().hex[:8]
    t0 = int(time.time() * 1000)
    base = 97000.0
    n = int(duration_sec)
    for i in range(n):
        for channel, window in (("price.crypto.twap", 60), ("price.crypto", None)):
            v = base + 40 * math.sin(i / 25.0) + (5 if channel == "price.crypto" else 0)
            env = {
                "v": 1, "channel": channel, "seq": i + 1, "ts": t0 + i * 1000,
                "payload": {"symbol": "btcusd", "value": v,
                            "full_accuracy_value": f"{v:.8f}",
                            "timestamp": t0 + i * 1000, "source": "chainlink"},
            }
            for r in envelope_to_rows(env, connection_id=connection_id):
                writer.append(r)
    writer.flush()
    return {"n_rows": n * 2, "n_env": n * 2, "n_snapshot": 0, "dropped_total": 0, "reconnects": 0, "dry_run": True}


def main() -> None:
    ap = argparse.ArgumentParser(description="Record PolyBolt TWAP+spot to Parquet (G1).")
    ap.add_argument("--duration-sec", type=float, default=3600)
    ap.add_argument("--out", default="data/raw")
    ap.add_argument("--dry-run", action="store_true", help="synthetic ticks, no network/creds")
    args = ap.parse_args()
    if args.dry_run:
        stats = asyncio.run(_dry_run(args.duration_sec, args.out))
    else:
        stats = asyncio.run(_record_once(args.duration_sec, args.out))
    print(json.dumps({"status": "done", **stats}, indent=2))


if __name__ == "__main__":
    main()
