from __future__ import annotations
from fastapi import APIRouter
from harness.schema import SourcesResponse, SourceReliability
from api.engine import EngineState

def get_sources_router(engine: EngineState) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["Trust & Adversity"])

    @router.get("/sources/reliability", response_model=SourcesResponse)
    def get_sources_reliability():
        details = engine.truth_discovery.get_source_details()
        if not details:
            # Fallback nominal sources list
            sources = [
                SourceReliability(
                    source_id="cwc_mithi_gauges",
                    source_type="sensor",
                    layer="HYD",
                    reliability=0.96,
                    staleness_h=0.1,
                    quarantined=False,
                    history=[0.94, 0.95, 0.96]
                ),
                SourceReliability(
                    source_id="scada_feeder_telemetry",
                    source_type="sensor",
                    layer="PWR",
                    reliability=0.92,
                    staleness_h=0.05,
                    quarantined=False,
                    history=[0.91, 0.92, 0.92]
                ),
                SourceReliability(
                    source_id="imdf_weather_numerical_model",
                    source_type="feed",
                    layer="WX",
                    reliability=0.98,
                    staleness_h=0.2,
                    quarantined=False,
                    history=[0.97, 0.98, 0.98]
                )
            ]
        else:
            sources = [SourceReliability(**d) for d in details]

        return SourcesResponse(
            sources=sources,
            quarantined_clusters=engine.citizen_trust.quarantined_clusters
        )

    return router
