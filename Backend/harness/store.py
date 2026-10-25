from __future__ import annotations
import os
import threading
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set
import duckdb
import pandas as pd
from harness.schema import CanonicalEvent

class AsOfStore:
    """
    Event-sourced canonical store enforcing strict temporal isolation.
    Rule: Downstream modules can only access data through view(as_of).
    No module receives a raw handle to the underlying mutable log.
    """
    def __init__(self, db_path: Optional[str] = None):
        self._lock = threading.RLock()
        self._seen_ids: Set[str] = set()
        self._events: List[Dict[str, Any]] = []
        self._con = duckdb.connect(database=":memory:")
        self._init_duckdb()

    def _init_duckdb(self):
        self._con.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id VARCHAR PRIMARY KEY,
                source_id VARCHAR,
                source_type VARCHAR,
                layer VARCHAR,
                zone_id VARCHAR,
                variable VARCHAR,
                value DOUBLE,
                event_time TIMESTAMP,
                ingest_time TIMESTAMP,
                issued_at TIMESTAMP,
                valid_for TIMESTAMP,
                quality DOUBLE,
                meta VARCHAR
            )
        """)

    def ingest(self, events: List[CanonicalEvent]) -> Dict[str, Any]:
        """
        Idempotent ingest of canonical events.
        Enforces deduplication on event_id.
        """
        accepted = 0
        duplicates = 0
        rejected = []
        new_rows = []

        with self._lock:
            for ev in events:
                if ev.event_id in self._seen_ids:
                    duplicates += 1
                    continue

                if ev.ingest_time < ev.event_time:
                    rejected.append({
                        "event_id": ev.event_id,
                        "reason": "ingest_time cannot precede physical event_time"
                    })
                    continue

                row = {
                    "event_id": ev.event_id,
                    "source_id": ev.source_id,
                    "source_type": ev.source_type.value,
                    "layer": ev.layer.value,
                    "zone_id": ev.zone_id,
                    "variable": ev.variable,
                    "value": float(ev.value),
                    "event_time": ev.event_time,
                    "ingest_time": ev.ingest_time,
                    "issued_at": ev.issued_at,
                    "valid_for": ev.valid_for,
                    "quality": float(ev.quality or 1.0),
                    "meta": str(ev.meta)
                }
                self._seen_ids.add(ev.event_id)
                self._events.append(row)
                new_rows.append(row)
                accepted += 1

            if new_rows:
                df = pd.DataFrame(new_rows)
                self._con.register("new_df", df)
                self._con.execute("INSERT INTO events SELECT * FROM new_df")
                self._con.unregister("new_df")

        watermark = (
            max((r["ingest_time"] for r in new_rows), default=datetime.now(timezone.utc)).isoformat()
        )
        return {
            "accepted": accepted,
            "duplicates": duplicates,
            "rejected": rejected,
            "watermark": watermark
        }

    def view(self, as_of: datetime) -> pd.DataFrame:
        """
        Strict as-of snapshot query.
        Returns only rows with:
          1. ingest_time <= as_of
          2. if issued_at is present (forecasts), issued_at <= as_of
        Nothing from future time is leaked.
        """
        with self._lock:
            query = """
                SELECT * FROM events
                WHERE ingest_time <= ?
                  AND (issued_at IS NULL OR issued_at <= ?)
                ORDER BY event_time ASC
            """
            return self._con.execute(query, [as_of, as_of]).df()

    def get_max_ingest_time(self, as_of: datetime) -> Optional[datetime]:
        """Returns the highest ingest_time visible at or before as_of."""
        with self._lock:
            query = """
                SELECT MAX(ingest_time) FROM events
                WHERE ingest_time <= ?
            """
            res = self._con.execute(query, [as_of]).fetchone()
            return res[0] if res and res[0] is not None else None

    def export_parquet(self, filepath: str):
        """Export snapshot of event log to Parquet."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with self._lock:
            self._con.execute(f"COPY events TO '{filepath}' (FORMAT PARQUET)")
