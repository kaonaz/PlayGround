"""Stream-health metrics for G1 (H1b): inter-arrival, gaps, dropped, TWAP-vs-spot."""
from __future__ import annotations

import numpy as np
import pandas as pd


def interarrival_stats(ts_ms: pd.Series) -> dict:
    d = ts_ms.sort_values().diff().dropna()
    if d.empty:
        return {"n": 0}
    return {
        "n": int(len(d) + 1),
        "p50_ms": float(d.quantile(0.5)),
        "p95_ms": float(d.quantile(0.95)),
        "max_ms": float(d.max()),
        "mean_ms": float(d.mean()),
    }


def summarize_raw(df: pd.DataFrame) -> dict:
    out: dict = {"rows": int(len(df))}
    if df.empty:
        return out
    for ch, g in df.groupby("channel"):
        out[str(ch)] = {
            "interarrival_payload_ts": interarrival_stats(g["payload_ts_ms"].dropna()),
            "dropped_sum": int(g["dropped"].fillna(0).sum()),
            "connections": int(g["connection_id"].nunique()),
            "sources": sorted(map(str, g["source"].dropna().unique().tolist())),
            "snapshots": int(g["is_snapshot"].sum()),
        }
    tw = df[df.channel == "price.crypto.twap"].copy()
    sp = df[df.channel == "price.crypto"].copy()
    if not tw.empty and not sp.empty:
        tw_v = pd.to_numeric(tw["value_str"], errors="coerce").dropna()
        sp_v = pd.to_numeric(sp["value_str"], errors="coerce").dropna()
        if not tw_v.empty and not sp_v.empty:
            out["twap_median"] = float(tw_v.median())
            out["spot_median"] = float(sp_v.median())
            out["twap_spot_median_abs_dev"] = float(abs(tw_v.median() - sp_v.median()))
    return out
