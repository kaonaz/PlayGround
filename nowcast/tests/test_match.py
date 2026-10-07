import pandas as pd

from nowcast.eval.g1_match import official_outcome, pick


def _tw():
    return pd.DataFrame([
        {"payload_ts_ms": 1000, "value_f": 100.0},
        {"payload_ts_ms": 2000, "value_f": 101.0},
        {"payload_ts_ms": 3000, "value_f": 102.0},
    ])


def test_boundary_rules():
    tw = _tw()
    assert float(pick(tw, 2000, "before")["value_f"]) == 100.0
    assert float(pick(tw, 2000, "on_or_before")["value_f"]) == 101.0
    assert float(pick(tw, 2000, "on_or_after")["value_f"]) == 101.0
    assert pick(tw, 500, "before") is None


def test_official_outcome_prices():
    s = {"outcomes": '["Up", "Down"]', "outcomePrices": '["1", "0"]'}
    assert official_outcome(s) == "Up"
    s2 = {"outcomes": ["Down", "Up"], "outcomePrices": ["0.9", "0.1"]}
    assert official_outcome(s2) == "Down"
