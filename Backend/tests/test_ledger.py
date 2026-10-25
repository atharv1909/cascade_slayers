import pytest
from datetime import datetime, timezone, timedelta
from harness.ledger import HashChainedLedger

def test_hash_chained_ledger_integrity():
    ledger = HashChainedLedger()
    t0 = datetime(2026, 7, 26, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Append valid forecast
    rec1 = ledger.append_forecast(
        forecast_id="fc_001",
        as_of=t0,
        data_max_ingest_time=t0 - timedelta(minutes=5),
        input_digest="sha256_sample1",
        model_version="1.0",
        outputs={"city_state": "WATCH"}
    )
    assert rec1["hash"] != ""

    # 2. Append second forecast
    t1 = t0 + timedelta(hours=1)
    rec2 = ledger.append_forecast(
        forecast_id="fc_002",
        as_of=t1,
        data_max_ingest_time=t1,
        input_digest="sha256_sample2",
        model_version="1.0",
        outputs={"city_state": "HIGH_RISK"}
    )
    assert rec2["prev_hash"] == rec1["hash"]

    # 3. Verify valid chain
    ok, n_recs, bad = ledger.verify_chain()
    assert ok is True
    assert n_recs == 2
    assert bad is None

    # 4. Temporal leakage rejection test: data_max_ingest_time > as_of must raise ValueError
    with pytest.raises(ValueError):
        ledger.append_forecast(
            forecast_id="fc_leak",
            as_of=t0,
            data_max_ingest_time=t0 + timedelta(minutes=10),
            input_digest="sha256_leak",
            model_version="1.0",
            outputs={}
        )
