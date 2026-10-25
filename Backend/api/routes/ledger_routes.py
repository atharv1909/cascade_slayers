from __future__ import annotations
from typing import Dict, Any, Optional
from fastapi import APIRouter, Path, HTTPException
from harness.schema import LedgerVerifyResponse, LedgerRecord
from harness.canary import run_leakage_canary_test
from api.engine import EngineState

def get_ledger_router(engine: EngineState) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["Auditing & Integrity"])

    @router.get("/ledger/verify", response_model=LedgerVerifyResponse)
    def verify_ledger():
        """
        Recomputes the cryptographic SHA-256 chain of all issued forecast records.
        Asserts temporal invariant data_max_ingest_time <= as_of.
        """
        ok, count, first_bad = engine.ledger.verify_chain()
        canary_ok, msg = run_leakage_canary_test(engine.store, engine.clock.as_of)

        return LedgerVerifyResponse(
            ok=ok,
            n_records=count,
            first_bad=first_bad,
            canary_passed=canary_ok
        )

    @router.get("/ledger/{forecast_id}")
    def get_ledger_record(
        forecast_id: str = Path(..., description="Unique forecast identifier")
    ):
        rec = engine.ledger.get_record(forecast_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Forecast record not found in ledger")
        return rec

    @router.get("/canary")
    def run_canary():
        """
        Executes live temporal leakage canary test:
        Injects a fabricated spike at t+6h and proves that predictions at t are bit-identical.
        """
        passed, msg = run_leakage_canary_test(engine.store, engine.clock.as_of)
        return {"passed": passed, "message": msg}

    return router
