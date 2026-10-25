import pytest
from datetime import datetime, timezone
from harness.store import AsOfStore
from harness.canary import run_leakage_canary_test

def test_leakage_canary():
    store = AsOfStore()
    as_of = datetime(2026, 7, 26, 12, 0, 0, tzinfo=timezone.utc)
    passed, msg = run_leakage_canary_test(store, as_of)
    assert passed is True
    assert "Passed" in msg
