from __future__ import annotations
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from harness.schema import RiskResponse
from api.engine import EngineState

def get_risk_router(engine: EngineState) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["Risk"])

    @router.get("/risk", response_model=RiskResponse)
    def get_risk(
        as_of: Optional[str] = Query(None, description="ISO timestamp for strict as-of isolation"),
        zone: Optional[str] = Query(None, description="Optional zone ID filter")
    ):
        as_of_dt = None
        if as_of:
            clean_as_of = as_of.strip().replace(" ", "+")
            if clean_as_of.endswith("Z"):
                clean_as_of = clean_as_of[:-1] + "+00:00"
            try:
                as_of_dt = datetime.fromisoformat(clean_as_of)
            except Exception:
                as_of_dt = None
        return engine.get_risk_state(as_of=as_of_dt, zone_id=zone)

    return router
