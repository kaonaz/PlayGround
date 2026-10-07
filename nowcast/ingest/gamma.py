"""Gamma fetcher — G1 step 2 (spec sections VI/VII).

Fetches resolved-market JSON (description/startDate/endDate/outcome + any
price/"beat" fields) BEFORE recording hypotheses are tested, and stores the
raw JSON verbatim plus a parsed summary with a per-market rule hash.

Public endpoints (no auth):
  GET {base}/markets?slug=<slug>
  GET {base}/events?slug=<event-slug>

Usage:
  python -m nowcast.ingest.gamma --slug btc-updown-5m-1234567890 --out data/gamma
  python -m nowcast.ingest.gamma --slugs-file slugs.txt --out data/gamma
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone

import requests

BASE = os.environ.get("GAMMA_BASE_URL", "https://gamma-api.polymarket.com")


def _get(path: str, params: dict | None = None, timeout: int = 30) -> requests.Response:
    r = requests.get(f"{BASE}{path}", params=params or {}, timeout=timeout)
    r.raise_for_status()
    return r


def _first(d: dict | list) -> dict | None:
    if isinstance(d, list):
        return d[0] if d else None
    if isinstance(d, dict):
        for key in ("data", "markets", "result"):
            if isinstance(d.get(key), list) and d[key]:
                return d[key][0]
        if "slug" in d or "question" in d:
            return d
    return None


def fetch_market_by_slug(slug: str) -> dict:
    # 1. /markets?slug= (works for older slugs)
    r = _get("/markets", {"slug": slug})
    m = _first(r.json())
    if m:
        return m
    # 2. /events?slug= (current 5m slugs live here); merge event + inner market
    r = _get("/events", {"slug": slug})
    ev = _first(r.json())
    if not ev:
        raise SystemExit(f"Gamma: no market/event for slug={slug}")
    inner = (ev.get("markets") or [{}])[0]
    merged = {**ev, **{k: v for k, v in inner.items() if v not in (None, "")}}
    merged.setdefault("description", ev.get("description", ""))
    return merged


def rule_hash(description: str, resolution_source: str = "") -> str:
    h = hashlib.sha256(f"{description or ''}\n{resolution_source or ''}".encode()).hexdigest()
    return h[:16]


def summarize(m: dict) -> dict:
    desc = m.get("description", "") or ""
    return {
        "slug": m.get("slug"),
        "question": m.get("question"),
        "description": desc,
        "startDate": m.get("startDate"),
        "endDate": m.get("endDate") or m.get("end_date") or m.get("resolutionDate"),
        "outcomes": m.get("outcomes"),
        "outcomePrices": m.get("outcomePrices"),
        "resolutionSource": m.get("resolutionSource") or m.get("resolution_source"),
        "groupItemTitle": m.get("groupItemTitle"),
        "closed": m.get("closed"),
        "resolution_rule_hash": rule_hash(desc, m.get("resolutionSource") or ""),
        # keep every key containing price/beat for manual inspection
        "price_like_fields": {k: m.get(k) for k in m if any(s in k.lower() for s in ("price", "beat", "strike", "twap", "chainlink"))},
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def save_slug(slug: str, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    m = fetch_market_by_slug(slug)
    raw_path = os.path.join(out_dir, f"{slug}.raw.json")
    with open(raw_path, "w") as f:
        json.dump(m, f, indent=2, default=str)
    summ = summarize(m)
    summ_path = os.path.join(out_dir, f"{slug}.summary.json")
    with open(summ_path, "w") as f:
        json.dump(summ, f, indent=2, default=str)
    print(f"[gamma] {slug}\n  start={summ['startDate']} end={summ['endDate']}\n  rule_hash={summ['resolution_rule_hash']}\n  -> {summ_path}")
    print(f"  RULE TEXT (read tie + TWAP window from this, do not assume):\n  {(summ['description'] or '')[:600]}")
    return summ_path


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch Gamma market JSON (G1).")
    ap.add_argument("--slug", default=None)
    ap.add_argument("--slugs-file", default=None)
    ap.add_argument("--out", default="data/gamma")
    args = ap.parse_args()
    slugs: list[str] = []
    if args.slug:
        slugs.append(args.slug)
    if args.slugs_file:
        with open(args.slugs_file) as f:
            slugs += [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    if not slugs:
        ap.error("provide --slug and/or --slugs-file")
    for s in slugs:
        save_slug(s, args.out)


if __name__ == "__main__":
    main()
