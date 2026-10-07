"""Backtest/live-prediction entrypoint — GATED (G2+).

Refuses to run until a PASSING G1 report exists. This is intentional:
spec section X.2 forbids writing/running the next stage before the
current gate passes.
"""
from __future__ import annotations

import glob
import json
import os
import sys


def g1_passed(reports_dir: str = "data/reports") -> bool:
    for path in sorted(glob.glob(os.path.join(reports_dir, "g1_match-*.json"))):
        try:
            rep = json.load(open(path))
            if rep.get("verdict") == "PASS" and rep.get("perfect_rules"):
                return True
        except Exception:
            continue
    return False


def main() -> None:
    print("G2+ backtest/prediction is GATED by G1 (spec Lampiran G).")
    if not g1_passed():
        print("BLOCKED: no PASSING data/reports/g1_match-*.json found.")
        print("Complete G1 first: record -> gamma -> match, then re-run.")
        sys.exit(2)
    print("G1 PASS found — G2 model work may begin (not implemented in this G1 slice).")
    sys.exit(0)


if __name__ == "__main__":
    main()
