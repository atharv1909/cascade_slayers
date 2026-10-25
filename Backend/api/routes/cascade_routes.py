from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Query
from harness.schema import CascadeResponse
from api.engine import EngineState

def get_cascade_router(engine: EngineState) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["Cascade"])

    @router.get("/cascade", response_model=CascadeResponse)
    def get_cascade(
        zone: Optional[str] = Query(None, description="Zone ID or 'city'")
    ):
        return engine.get_cascade_info()

    return router
