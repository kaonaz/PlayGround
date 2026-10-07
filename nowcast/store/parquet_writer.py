"""Parquet writer with time-based rotation. One file per hour by default."""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone

import pyarrow as pa
import pyarrow.parquet as pq

from .schema import RAW_SCHEMA


class RawParquetWriter:
    def __init__(self, out_dir: str, prefix: str = "polybolt"):
        self.out_dir = out_dir
        self.prefix = prefix
        os.makedirs(out_dir, exist_ok=True)
        self._rows: list[dict] = []
        self._bucket: str | None = None

    def _bucket_for(self, recv_wall_ms: int) -> str:
        dt = datetime.fromtimestamp(recv_wall_ms / 1000, tz=timezone.utc)
        return dt.strftime("%Y%m%dT%H")

    def append(self, row: dict) -> None:
        b = self._bucket_for(row["recv_wall_ms"])
        if self._bucket is None:
            self._bucket = b
        if b != self._bucket:
            self.flush()
            self._bucket = b
        self._rows.append(row)

    def flush(self) -> str | None:
        if not self._rows:
            return None
        assert self._bucket is not None
        # normalize rows to schema columns
        cols: dict[str, list] = {f.name: [] for f in RAW_SCHEMA}
        for r in self._rows:
            for f in RAW_SCHEMA:
                cols[f.name].append(r.get(f.name))
        table = pa.table(cols, schema=RAW_SCHEMA)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        path = os.path.join(self.out_dir, f"{self.prefix}-{self._bucket}-{stamp}.parquet")
        pq.write_table(table, path)
        n = len(self._rows)
        self._rows = []
        print(f"[store] flushed {n} rows -> {path}", flush=True)
        return path

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.flush()
