"""G1 run entrypoint (thin wrapper over ingest + eval).

Step order per spec section VIII — one file per step:
  1. python -m nowcast.run.live --step record   (1h PolyBolt record)
  2. python -m nowcast.run.live --step gamma    (fetch 1-2 resolved markets)
  3. python -m nowcast.run.live --step match    (boundary-rule report)

G2+ model/training/execution entrypoints are intentionally absent:
see nowcast/run/backtest.py which refuses to run until G1 passes.
"""
from __future__ import annotations

import argparse
import subprocess
import sys


def sh(*cmd: str) -> None:
    print("+", " ".join(cmd), flush=True)
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(r.returncode)


def main() -> None:
    ap = argparse.ArgumentParser(description="G1 runner (record/gamma/match). NO trading.")
    ap.add_argument("--step", required=True, choices=["record", "gamma", "match", "all"])
    ap.add_argument("--duration-sec", type=float, default=3600)
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--gamma-dir", default="data/gamma")
    ap.add_argument("--reports", default="data/reports")
    ap.add_argument("--slug", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.step in ("record", "all"):
        cmd = [sys.executable, "-m", "nowcast.ingest.polybolt_ws",
               "--duration-sec", str(args.duration_sec), "--out", args.raw]
        if args.dry_run:
            cmd.append("--dry-run")
        sh(*cmd)
    if args.step in ("gamma", "all"):
        if not args.slug:
            print("record done. Next: re-run with --step gamma --slug btc-updown-5m-<epoch> (1-2 resolved markets).")
        else:
            sh(sys.executable, "-m", "nowcast.ingest.gamma", "--slug", args.slug, "--out", args.gamma_dir)
    if args.step in ("match", "all"):
        sh(sys.executable, "-m", "nowcast.eval.g1_match",
           "--raw", args.raw, "--gamma", args.gamma_dir, "--out", args.reports)


if __name__ == "__main__":
    main()
