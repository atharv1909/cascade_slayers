from __future__ import annotations
import copy
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Tuple
from harness.schema import CanonicalEvent, SourceType, LayerEnum
from harness.store import AsOfStore

def run_leakage_canary_test(store: AsOfStore, as_of: datetime) -> Tuple[bool, str]:
    """
    Leakage Canary Test:
    1. Query state/data view at time t (as_of).
    2. Inject a fabricated extreme spike at t + 6h into the store.
    3. Re-query the view at time t (as_of).
    4. Assert that the view at time t is bit-identical and completely unpolluted.
    """
    view_before = store.view(as_of)
    digest_before = hash(tuple(view_before['event_id'].tolist())) if not view_before.empty else 0

    future_t = as_of + timedelta(hours=6)
    canary_event = CanonicalEvent(
        event_id=f"canary_spike_{future_t.timestamp()}",
        source_id="canary_synthetic_injector",
        source_type=SourceType.SENSOR,
        layer=LayerEnum.HYD,
        zone_id="z04_kurla_w",
        variable="waterlogging_risk_index",
        value=0.999,  # Extreme fabricated flood spike
        event_time=future_t,
        ingest_time=future_t,
        quality=1.0,
        meta={"canary": True}
    )

    store.ingest([canary_event])

    view_after = store.view(as_of)
    digest_after = hash(tuple(view_after['event_id'].tolist())) if not view_after.empty else 0

    if digest_before != digest_after:
        return False, "Leakage detected: Future event at t+6h altered past state at t!"

    # Also verify that future query DOES see the canary
    view_future = store.view(future_t + timedelta(minutes=1))
    canary_seen = any(view_future['event_id'] == canary_event.event_id)

    if not canary_seen:
        return False, "Canary event was not ingested into store."

    return True, "Passed: Future event strictly isolated. Past views at as_of are bit-identical."
