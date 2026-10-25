from __future__ import annotations
from fastapi import APIRouter
from api.engine import EngineState
from adapters.open_meteo import OpenMeteoAdapter
from adapters.usgs import USGSAdapter

def get_adapters_router(engine: EngineState) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["Data Adapters"])
    om_adapter = OpenMeteoAdapter()
    usgs_adapter = USGSAdapter()

    @router.get("/adapters")
    def get_adapters():
        """Returns the data adapter registry showing live vs replay status and lag."""
        return engine.adapters.get_all()

    @router.post("/adapters/fetch")
    def trigger_live_fetch():
        """Fetches live external feeds from Open-Meteo and USGS and ingests them into store."""
        om_events = om_adapter.fetch_forecast()
        usgs_events = usgs_adapter.fetch_live_events()

        total = len(om_events) + len(usgs_events)
        if total > 0:
            engine.store.ingest(om_events + usgs_events)
            engine.adapters.update_status("open_meteo_live", mode="LIVE", status="CONNECTED", lag_s=12)
            engine.adapters.update_status("usgs_earthquake_live", mode="LIVE", status="CONNECTED", lag_s=25)

        return {"fetched_events": total, "status": "INGESTED_LIVE"}

    return router
