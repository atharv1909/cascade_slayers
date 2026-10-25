from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any
import requests
from harness.schema import CanonicalEvent, SourceType, LayerEnum

class USGSAdapter:
    """
    Live adapter fetching real-time seismic events from USGS Earthquake GeoJSON feed.
    Falls back to cached snapshot when offline.
    """
    def __init__(self, cache_file: Optional[str] = None):
        from harness.paths import get_project_root
        if cache_file is None:
            cache_file = os.path.join(get_project_root(), "adapters", "usgs_cached.json")
        self.cache_file = cache_file

    def fetch_live_events(self) -> List[CanonicalEvent]:
        url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
        now = datetime.now(timezone.utc)
        events: List[CanonicalEvent] = []

        try:
            resp = requests.get(url, timeout=4.0)
            if resp.status_code == 200:
                data = resp.json()
                os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(data, f)
            else:
                data = self._read_cache()
        except Exception:
            data = self._read_cache()

        features = data.get("features", [])
        for f in features:
            props = f.get("properties", {})
            mag = float(props.get("mag") or 1.0)
            time_ms = props.get("time") or int(now.timestamp() * 1000)
            ev_dt = datetime.fromtimestamp(time_ms / 1000.0, tz=timezone.utc)
            code = props.get("code") or str(time_ms)

            events.append(CanonicalEvent(
                event_id=f"live_usgs_{code}",
                source_id="usgs_earthquake_live",
                source_type=SourceType.FEED,
                layer=LayerEnum.SEI,
                zone_id="z04_kurla_w",
                variable="shaking_intensity_mmi",
                value=float(min(12.0, max(1.0, 1.25 * mag))),
                event_time=ev_dt,
                ingest_time=now,
                quality=0.98,
                meta={"mag": mag, "place": props.get("place", "Global Seismic Event"), "live": True}
            ))

        return events

    def _read_cache(self) -> Dict[str, Any]:
        if os.path.exists(self.cache_file):
            with open(self.cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"features": []}
