import pytest
from datetime import datetime, timezone
from harness.schema import CanonicalEvent, SourceType, LayerEnum

def test_canonical_event_validation():
    ev = CanonicalEvent(
        event_id="ev_test_01",
        source_id="gauge_42",
        source_type=SourceType.SENSOR,
        layer=LayerEnum.HYD,
        zone_id="z04_kurla_w",
        variable="waterlogging_risk_index",
        value=0.75,
        event_time=datetime.now(timezone.utc),
        ingest_time=datetime.now(timezone.utc),
        quality=0.95
    )
    assert ev.layer == LayerEnum.HYD
    assert ev.value == 0.75

    # Invalid quality > 1.0 should fail
    with pytest.raises(Exception):
        CanonicalEvent(
            event_id="ev_bad",
            source_id="gauge_42",
            source_type=SourceType.SENSOR,
            layer=LayerEnum.HYD,
            zone_id="z04_kurla_w",
            variable="waterlogging_risk_index",
            value=0.75,
            event_time=datetime.now(timezone.utc),
            ingest_time=datetime.now(timezone.utc),
            quality=1.5
        )
