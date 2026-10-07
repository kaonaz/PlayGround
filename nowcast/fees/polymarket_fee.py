"""Polymarket taker-fee model (G3-gated; unit-tested here in G1).

Spec Lampiran C (effective 2026-10-06, re-verify periodically):
  fee_per_share = 0.07 * p * (1 - p)   [Crypto category]
  rounded to 5 decimals, minimum 0.00001 USDC, 0 at p in {0, 1}.
Maker fee is 0 with 20% rebate (separate execution scenario, not this function).
"""
from __future__ import annotations

RATE = 0.07
DECIMALS = 5
MINIMUM = 0.00001


def taker_fee_per_share(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    raw = RATE * p * (1.0 - p)
    fee = round(raw, DECIMALS)
    if fee < MINIMUM:
        return 0.0
    return fee


def edge_net(p_model: float, ask: float) -> float:
    """Net edge screening per snapshot: p_model - ask - fee(ask)."""
    return p_model - ask - taker_fee_per_share(ask)
