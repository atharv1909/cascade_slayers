from __future__ import annotations
import math
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import numpy as np
import pandas as pd
from harness.schema import CanonicalEvent, SourceType, LayerEnum

def generate_canonical_events(
    truth_df: pd.DataFrame,
    forecasts_df: pd.DataFrame,
    start_time: datetime,
    rng: np.random.Generator
) -> List[CanonicalEvent]:
    """
    Transforms truth simulation states into physical sensor and feed observations.
    Assigns realistic sensor IDs, noise, and baseline latency.
    """
    events: List[CanonicalEvent] = []

    # Map layer string to SourceType
    source_type_map = {
        "WX": SourceType.FEED,
        "HYD": SourceType.SENSOR,
        "TRF": SourceType.SENSOR,
        "PWR": SourceType.SENSOR,
        "EMS": SourceType.OFFICIAL,
        "HOS": SourceType.OFFICIAL,
        "HLT": SourceType.OFFICIAL,
        "AIR": SourceType.SENSOR,
        "SEI": SourceType.SENSOR,
        "COM": SourceType.CITIZEN
    }

    # Process truth series
    for idx, row in truth_df.iterrows():
        t_h = int(row["hour"])
        layer = row["layer"]
        zid = row["zone_id"]
        var = row["variable"]
        true_val = float(row["value"])

        ev_time = start_time + timedelta(hours=t_h)
        # Small measurement noise (0.5% - 2%)
        noise = rng.normal(0, max(0.01, abs(true_val) * 0.015))
        observed_val = max(0.0, true_val + noise)

        # Base nominal latency (2 to 6 minutes)
        latency_min = rng.uniform(2.0, 6.0)
        ingest_time = ev_time + timedelta(minutes=latency_min)

        source_id = f"{layer.lower()}_sensor_{zid}_{var}"

        events.append(CanonicalEvent(
            event_id=f"ev_{layer}_{zid}_{var}_{t_h}",
            source_id=source_id,
            source_type=source_type_map.get(layer, SourceType.SENSOR),
            layer=LayerEnum(layer),
            zone_id=zid,
            variable=var,
            value=float(observed_val),
            event_time=ev_time,
            ingest_time=ingest_time,
            quality=0.98,
            meta={"simulated": True}
        ))

    # Process issued weather forecast covariates
    for idx, row in forecasts_df.iterrows():
        issued_h = int(row["issued_hour"])
        valid_h = int(row["valid_hour"])
        zid = row["zone_id"]
        var = row["variable"]
        fc_val = float(row["forecast_value"])

        issued_time = start_time + timedelta(hours=issued_h)
        valid_time = start_time + timedelta(hours=valid_h)

        events.append(CanonicalEvent(
            event_id=f"fc_wx_{zid}_{var}_i{issued_h}_v{valid_h}",
            source_id="imdf_weather_numerical_model",
            source_type=SourceType.FORECAST,
            layer=LayerEnum.WX,
            zone_id=zid,
            variable=f"forecast_{var}",
            value=fc_val,
            event_time=valid_time,
            ingest_time=issued_time + timedelta(minutes=10), # ready shortly after issuance
            issued_at=issued_time,
            valid_for=valid_time,
            quality=0.92,
            meta={"lead_h": int(row["lead_h"])}
        ))

    events.sort(key=lambda x: x.ingest_time)
    return events
