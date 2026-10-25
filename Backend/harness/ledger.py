from __future__ import annotations
import json
import hashlib
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from harness.schema import LedgerRecord

class HashChainedLedger:
    """
    Cryptographically verified hash-chained forecast ledger.
    Every forecast emitted by the risk engine is immutably appended to a SHA-256 chain.
    Asserts at write time that data_max_ingest_time <= as_of.
    """
    def __init__(self):
        self._lock = threading.RLock()
        self._records: List[Dict[str, Any]] = []
        self._records_by_id: Dict[str, Dict[str, Any]] = {}
        self._latest_hash = "0" * 64

    @staticmethod
    def canonical_json(data: Dict[str, Any]) -> str:
        """Deterministic canonical JSON serialization for hashing."""
        return json.dumps(data, sort_keys=True, separators=(',', ':'), default=str)

    def append_forecast(
        self,
        forecast_id: str,
        as_of: datetime,
        data_max_ingest_time: datetime,
        input_digest: str,
        model_version: str,
        outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        with self._lock:
            # Enforce temporal integrity
            if data_max_ingest_time > as_of:
                raise ValueError(
                    f"Temporal leakage violation: data_max_ingest_time ({data_max_ingest_time}) > as_of ({as_of})"
                )

            record_payload = {
                "forecast_id": forecast_id,
                "as_of": as_of.isoformat(),
                "data_max_ingest_time": data_max_ingest_time.isoformat(),
                "input_digest": input_digest,
                "model_version": model_version,
                "outputs": outputs,
                "prev_hash": self._latest_hash
            }

            canonical_str = self.canonical_json(record_payload)
            record_hash = hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()

            full_record = {**record_payload, "hash": record_hash}
            self._records.append(full_record)
            self._records_by_id[forecast_id] = full_record
            self._latest_hash = record_hash
            return full_record

    def verify_chain(self) -> Tuple[bool, int, Optional[str]]:
        """
        Recomputes the SHA-256 chain from the genesis record to the head.
        Returns: (ok, n_records, first_bad_id)
        """
        with self._lock:
            expected_prev = "0" * 64
            for idx, rec in enumerate(self._records):
                if rec["prev_hash"] != expected_prev:
                    return False, len(self._records), rec["forecast_id"]

                check_payload = {
                    "forecast_id": rec["forecast_id"],
                    "as_of": rec["as_of"],
                    "data_max_ingest_time": rec["data_max_ingest_time"],
                    "input_digest": rec["input_digest"],
                    "model_version": rec["model_version"],
                    "outputs": rec["outputs"],
                    "prev_hash": rec["prev_hash"]
                }
                computed_hash = hashlib.sha256(self.canonical_json(check_payload).encode('utf-8')).hexdigest()
                if computed_hash != rec["hash"]:
                    return False, len(self._records), rec["forecast_id"]

                # Check temporal invariant
                as_of_dt = datetime.fromisoformat(rec["as_of"])
                ingest_dt = datetime.fromisoformat(rec["data_max_ingest_time"])
                if ingest_dt > as_of_dt:
                    return False, len(self._records), rec["forecast_id"]

                expected_prev = computed_hash

            return True, len(self._records), None

    def get_record(self, forecast_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._records_by_id.get(forecast_id)

    def get_all_records(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._records)
