import math

from nowcast.fees.polymarket_fee import edge_net, taker_fee_per_share


def test_fee_table_values():
    assert taker_fee_per_share(0.50) == 0.0175
    assert taker_fee_per_share(0.70) == 0.0147
    assert taker_fee_per_share(0.30) == 0.0147
    assert abs(taker_fee_per_share(0.87) - 0.00792) < 1e-9  # rounds to 0.00792
    assert taker_fee_per_share(0.90) == 0.0063
    assert taker_fee_per_share(0.10) == 0.0063


def test_fee_symmetry_and_rounding():
    for p in [0.05, 0.13, 0.25, 0.42, 0.61, 0.83, 0.95]:
        assert taker_fee_per_share(p) == taker_fee_per_share(1 - p)
        f = taker_fee_per_share(p)
        assert f == round(f, 5)


def test_fee_minimum_and_edges():
    assert taker_fee_per_share(0.0) == 0.0
    assert taker_fee_per_share(1.0) == 0.0
    assert taker_fee_per_share(0.00001) == 0.0  # rounds below minimum -> 0
    assert taker_fee_per_share(0.0001) == 0.00001  # rounds to exactly the minimum


def test_edge_screening():
    assert edge_net(0.60, 0.50) == 0.60 - 0.50 - 0.0175
