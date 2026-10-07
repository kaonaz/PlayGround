"""G1 matcher — G1 step 3 (spec section VII).

Goal: prove the official outcome can be computed deterministically from the
recorded TWAP stream, under exactly one boundary rule.

For each window [startDate, endDate] from Gamma summaries:
  S_open / S_end are taken from the TWAP channel (price.crypto.twap) only.
  Three boundary rules are scored SEPARATELY (H1a):
    before       = last tick with payload_ts strictly < bound
    on_or_before = last tick with payload_ts <= bound
    on_or_after  = first tick with payload_ts >= bound
  Outcome: Up if S_end >= S_open else Down.
    (tie->Up is the UNCONFIRMED default; override with --tie down after
     reading the market's rule text. Ties are always counted & reported.)

Inputs:
  --raw   parquet file or directory (raw store)
  --gamma data/gamma dir (*.summary.json) — needs startDate/endDate + outcome
  --out   report dir

Outcome parsing: Gamma `outcomes`/`outcomePrices` shapes vary; we resolve the
official side via, in order: explicit UMA/outcome field, outcomePrices argmax
mapped onto outcomes names, groupItemTitle. Anything ambiguous is reported as
UNKNOWN (an explained exception, never silently mapped).

Verdict:
  PASS       one rule == 100% match, exceptions explained
  INVESTIGATE any unexplained mismatch
  HALTED      no rule matches and no cause found (manual judgement, reported)
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
from datetime import datetime, timezone

import pandas as pd

RULES = ("before", "on_or_before", "on_or_after")


def parse_ms(x) -> int | None:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        v = int(x)
        return v * 1000 if v < 10_000_000_000 else v  # sec -> ms guard
    try:
        dt = datetime.fromisoformat(str(x).replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)
    except ValueError:
        return None


def official_outcome(summary: dict) -> str:
    blob = json.dumps(summary).lower()
    # explicit fields first
    for key in ("resolvedOutcome", "resolved_outcome", "outcome", "resolution"):
        v = summary.get(key)
        if isinstance(v, str) and v.strip().lower() in ("up", "down", "yes", "no"):
            s = v.strip().lower()
            return "Up" if s in ("up", "yes") else "Down"
    outcomes = summary.get("outcomes")
    prices = summary.get("outcomePrices")
    try:
        names = json.loads(outcomes) if isinstance(outcomes, str) else outcomes
        pr = [float(x) for x in (json.loads(prices) if isinstance(prices, str) else (prices or []))]
        if isinstance(names, list) and len(names) == 2 and len(pr) == 2:
            winner = names[int(pr[1] > pr[0])]
            w = str(winner).lower()
            if "up" in w or "yes" in w:
                return "Up"
            if "down" in w or "no" in w:
                return "Down"
    except Exception:
        pass
    t = str(summary.get("groupItemTitle", "")).lower()
    if "up" in t:
        return "Up"
    if "down" in t:
        return "Down"
    if '"up"' in blob and '"down"' not in blob:
        return "Up?"
    return "UNKNOWN"


def pick(tw: pd.DataFrame, bound_ms: int, rule: str):
    ts = tw["payload_ts_ms"].to_numpy()
    if rule == "before":
        cand = tw[ts < bound_ms]
        return cand.iloc[-1] if len(cand) else None
    if rule == "on_or_before":
        cand = tw[ts <= bound_ms]
        return cand.iloc[-1] if len(cand) else None
    cand = tw[ts >= bound_ms]  # on_or_after
    return cand.iloc[0] if len(cand) else None


def main() -> None:
    ap = argparse.ArgumentParser(description="G1 outcome matcher (TWAP boundary rules).")
    ap.add_argument("--raw", required=True, help="parquet file or dir")
    ap.add_argument("--gamma", required=True, help="dir with *.summary.json")
    ap.add_argument("--out", default="data/reports")
    ap.add_argument("--tie", default="Up", choices=["Up", "Down"])
    args = ap.parse_args()

    raws = glob.glob(os.path.join(args.raw, "*.parquet")) if os.path.isdir(args.raw) else [args.raw]
    if not raws:
        raise SystemExit(f"no parquet found in {args.raw}")
    df = pd.concat([pd.read_parquet(p) for p in raws], ignore_index=True)
    tw = df[df.channel == "price.crypto.twap"].copy()
    tw["value_f"] = pd.to_numeric(tw["value_str"], errors="coerce")
    tw = tw.dropna(subset=["payload_ts_ms", "value_f"]).sort_values("payload_ts_ms").reset_index(drop=True)

    summaries = sorted(glob.glob(os.path.join(args.gamma, "*.summary.json")))
    if not summaries:
        raise SystemExit(f"no *.summary.json in {args.gamma}")
    rows: list[dict] = []
    for path in summaries:
        s = json.load(open(path))
        start_ms, end_ms = parse_ms(s.get("startDate")), parse_ms(s.get("endDate"))
        if start_ms is None or end_ms is None:
            rows.append({"slug": s.get("slug"), "status": "SKIP_NO_DATES"})
            continue
        off = official_outcome(s)
        entry: dict = {"slug": s.get("slug"), "start_ms": start_ms, "end_ms": end_ms,
                       "official": off, "rule_hash": s.get("resolution_rule_hash")}
        for rule in RULES:
            ro = pick(tw, start_ms, rule)
            re = pick(tw, end_ms, rule)
            if ro is None or re is None:
                entry[rule] = {"status": "NO_TICK"}
                continue
            so, se = float(ro["value_f"]), float(re["value_f"])
            if se == so:
                calc = args.tie
                tie = True
            else:
                calc = "Up" if se >= so else "Down"
                tie = False
            entry[rule] = {"S_open": so, "S_end": se, "d": se - so, "tie": tie,
                           "calc": calc, "match": (calc == off) if not off.endswith("?") and off != "UNKNOWN" else None,
                           "open_ts": int(ro["payload_ts_ms"]), "end_ts": int(re["payload_ts_ms"])}
        rows.append(entry)

    # aggregate per rule
    agg: dict = {}
    for rule in RULES:
        scored = [r for r in rows if isinstance(r.get(rule), dict) and r[rule].get("match") is not None]
        matched = [r for r in scored if r[rule]["match"]]
        agg[rule] = {"scored": len(scored), "matched": len(matched),
                     "rate": (len(matched) / len(scored)) if scored else None}
    perfect = [r for r in RULES if agg[r]["scored"] and agg[r]["matched"] == agg[r]["scored"]]
    verdict = "PASS" if perfect else "INVESTIGATE"
    if not any(agg[r]["scored"] for r in RULES):
        verdict = "HALTED_NO_OVERLAP"

    os.makedirs(args.out, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "tie_assumed": args.tie,
              "twap_rows": int(len(tw)), "windows": len(rows),
              "per_rule": agg, "perfect_rules": perfect, "verdict": verdict, "windows_detail": rows}
    jp = os.path.join(args.out, f"g1_match-{stamp}.json")
    json.dump(report, open(jp, "w"), indent=2)
    # markdown
    mism = []
    for r in rows:
        for rule in RULES:
            c = r.get(rule)
            if isinstance(c, dict) and c.get("match") is False:
                mism.append((r["slug"], rule, c))
    mp = os.path.join(args.out, f"g1_match-{stamp}.md")
    with open(mp, "w") as f:
        f.write(f"# G1 match report — {stamp}Z\n\nverdict: **{verdict}** (tie assumed: {args.tie})\n\n")
        f.write(f"twap rows: {len(tw)} · windows: {len(rows)}\n\n")
        f.write("| rule | matched/scored | rate |\n|---|---|---|\n")
        for rule in RULES:
            a = agg[rule]
            rate = f"{a['rate']:.3f}" if a["rate"] is not None else "n/a"
            f.write(f"| {rule} | {a['matched']}/{a['scored']} | {rate} |\n")
        f.write(f"\nperfect rules: {perfect or '—'}\n\n")
        if mism:
            f.write("## mismatches (explain each one-by-one per H1c)\n\n| slug | rule | S_open | S_end | d | calc | official |\n|---|---|---|---|---|---|---|\n")
            for slug, rule, c in mism:
                f.write(f"| {slug} | {rule} | {c['S_open']} | {c['S_end']} | {c['d']:.6g} | {c['calc']} | — |\n")
        else:
            f.write("no mismatches on scored windows.\n")
        f.write("\nGate: PASS requires ONE rule at 100% with every exception explained; else STOP & investigate.\n")
    print(json.dumps({"verdict": verdict, "per_rule": agg, "json": jp, "md": mp}, indent=2))


if __name__ == "__main__":
    main()
