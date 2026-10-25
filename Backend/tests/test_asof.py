import pytest
from datetime import datetime, timezone, timedelta
from harness.schema import CanonicalEvent, SourceType, LayerEnum
from harness.store import AsOfStore

def test_strict_asof_isolation():
    store = AsOfStore()
    t0 = datetime(2026, 7, 26, 12, 0, 0, tzinfo=timezone.utc)
    t_future = t0 + timedelta(hours=6)

    ev_past = CanonicalEvent(
        event_id="ev_001",
        source_id="gauge_01",
        source_type=SourceType.SENSOR,
        layer=LayerEnum.HYD,
        zone_id="z04_kurla_w",
        variable="drain_load_ratio",
        value=0.45,
        event_time=t0 - timedelta(hours=1),
        ingest_time=t0 - timedelta(minutes=30),
        quality=1.0
    )

    ev_future = CanonicalEvent(
        event_id="ev_002",
        source_id="gauge_01",
        source_type=SourceType.SENSOR,
        layer=LayerEnum.HYD,
        zone_id="z04_kurla_w",
        variable="drain_load_ratio",
        value=1.95,
        event_time=t_future,
        ingest_time=t_future,
        quality=1.0
    )

    store.ingest([ev_past, ev_future])

    # View at t0 should only see ev_past
    view_t0 = store.view(t0)
    assert len(view_t0) == 1
    assert view_t0.iloc[0]["event_id"] == "ev_001"

    # View at t_future should see both
    view_future = store.view(t_future + timedelta(minutes=1))
    assert len(view_future) == 2
