"""Raw-store schema for G1 (spec section VIII).

One row per price point. Snapshot batches are expanded so each point keeps
its own payload timestamp. Decimal values are ALSO kept as strings +
full raw JSON so nothing is lost to float rounding.
"""
from __future__ import annotations

import pyarrow as pa

RAW_SCHEMA = pa.schema(
    [
        ("recv_mono_ns", pa.int64()),
        ("recv_wall_ms", pa.int64()),
        ("channel", pa.string()),
        ("symbol", pa.string()),
        ("source", pa.string()),  # vendor: chainlink/pyth/... — re-read every msg & reconnect
        ("seq", pa.int64()),
        ("ts_ms", pa.int64()),  # producer event time (envelope ts)
        ("payload_ts_ms", pa.int64()),  # point timestamp (payload.timestamp)
        ("value_str", pa.string()),  # str(value) verbatim
        ("full_accuracy_value", pa.string()),
        ("window_seconds", pa.int64()),  # 60 for TWAP, null for spot
        ("is_snapshot", pa.bool_()),
        ("dropped", pa.int64()),
        ("raw_json", pa.string()),
        ("connection_id", pa.string()),
    ]
)

RAW_COLUMNS = [f.name for f in RAW_SCHEMA]
