from __future__ import annotations
from fastapi import APIRouter, Body
from harness.schema import IngestBatchRequest, IngestBatchResponse
from api.engine import EngineState

def get_ingest_router(engine: EngineState) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["Ingest"])

    @router.post("/ingest", response_model=IngestBatchResponse)
    def post_ingest(batch: IngestBatchRequest = Body(...)):
        """
        Production-grade batch ingestion endpoint for all real and simulated feeds.
        Idempotent on event_id, validates Pydantic schema, enforces temporal sequencing.
        """
        res = engine.store.ingest(batch.events)
        return IngestBatchResponse(
            accepted=res["accepted"],
            duplicates=res["duplicates"],
            rejected=res["rejected"],
            watermark=res["watermark"]
        )

    return router
