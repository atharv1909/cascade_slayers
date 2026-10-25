from __future__ import annotations
from fastapi import APIRouter
from eval.report import generate_evaluation_scoreboard
from api.engine import EngineState

def get_eval_router(engine: EngineState) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["Evaluation & Scoreboard"])

    @router.get("/metrics/eval")
    def get_metrics_eval():
        """
        Returns full empirical evaluation scoreboard:
        Lead-time vs FAR curve, reliability diagrams, ECE, fault sweep degradation,
        held-out city results, baseline and ablation tables.
        """
        return generate_evaluation_scoreboard()

    return router
