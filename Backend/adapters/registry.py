from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, Any, List

class AdapterRegistry:
    """
    Tracks data adapters feeding the canonical ingest pipeline.
    Documents whether each adapter is operating in REPLAY, CACHED, or LIVE mode.
    """
    def __init__(self):
        self.adapters = {
            "imdf_monsoon_radar": {
                "source_id": "imdf_monsoon_radar",
                "name": "IMD Doppler Weather Radar Feed",
                "layer": "WX",
                "mode": "REPLAY",
                "status": "HEALTHY",
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "lag_seconds": 120
            },
            "cwc_mithi_gauges": {
                "source_id": "cwc_mithi_gauges",
                "name": "Central Water Commission Mithi River Telemetry",
                "layer": "HYD",
                "mode": "REPLAY",
                "status": "HEALTHY",
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "lag_seconds": 95
            },
            "scada_feeder_telemetry": {
                "source_id": "scada_feeder_telemetry",
                "name": "DISCOM SCADA Substation & Feeder Monitoring",
                "layer": "PWR",
                "mode": "REPLAY",
                "status": "HEALTHY",
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "lag_seconds": 45
            },
            "open_meteo_live": {
                "source_id": "open_meteo_live",
                "name": "Open-Meteo Numerical Weather Prediction API",
                "layer": "WX",
                "mode": "LIVE",
                "status": "CONNECTED",
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "lag_seconds": 18
            },
            "usgs_earthquake_live": {
                "source_id": "usgs_earthquake_live",
                "name": "USGS Real-Time Earthquake GeoJSON Feed",
                "layer": "SEI",
                "mode": "LIVE",
                "status": "CONNECTED",
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "lag_seconds": 30
            },
            "cpcb_air_quality": {
                "source_id": "cpcb_air_quality",
                "name": "CPCB Continuous Ambient Air Quality Monitors",
                "layer": "AIR",
                "mode": "REPLAY",
                "status": "HEALTHY",
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "lag_seconds": 300
            },
            "citizen_mobile_dispatch": {
                "source_id": "citizen_mobile_dispatch",
                "name": "Civil Protection Emergency Mobile Reporting Network",
                "layer": "COM",
                "mode": "REPLAY",
                "status": "HEALTHY",
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "lag_seconds": 10
            }
        }

    def get_all(self) -> List[Dict[str, Any]]:
        return list(self.adapters.values())

    def update_status(self, source_id: str, mode: str, status: str, lag_s: int):
        if source_id in self.adapters:
            self.adapters[source_id]["mode"] = mode
            self.adapters[source_id]["status"] = status
            self.adapters[source_id]["last_seen"] = datetime.now(timezone.utc).isoformat()
            self.adapters[source_id]["lag_seconds"] = lag_s
