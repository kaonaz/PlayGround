from nowcast.ingest.polybolt_ws import envelope_to_rows


def test_envelope_live_update_shape():
    env = {"v": 1, "channel": "price.crypto.twap", "seq": 2, "ts": 1788973001000,
           "payload": {"symbol": "btcusd", "value": 64126.0,
                       "full_accuracy_value": "64126.00000000",
                       "timestamp": 1788973001000, "source": "chainlink"}}
    rows = envelope_to_rows(env, connection_id="c1")
    assert len(rows) == 1
    r = rows[0]
    assert r["channel"] == "price.crypto.twap"
    assert r["window_seconds"] == 60
    assert r["is_snapshot"] is False
    assert r["value_str"] == "64126.0"
    assert r["source"] == "chainlink"


def test_envelope_snapshot_expands():
    env = {"v": 1, "channel": "price.crypto", "seq": 1, "ts": 1788973000000,
           "snapshot": True,
           "payload": {"symbol": "btcusd", "source": "chainlink",
                       "data": [{"timestamp": 1, "value": 1.5, "full_accuracy_value": "1.50000000"},
                                {"timestamp": 2, "value": 2.5, "full_accuracy_value": "2.50000000"}]}}
    rows = envelope_to_rows(env, connection_id="c1")
    assert len(rows) == 2
    assert all(r["is_snapshot"] for r in rows)
    assert rows[0]["payload_ts_ms"] == 1 and rows[1]["payload_ts_ms"] == 2
