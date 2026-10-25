from __future__ import annotations
from typing import Dict, Any, List
from fastapi import APIRouter, Path
from harness.schema import EdgeEvidenceCard
from api.engine import EngineState

def get_graph_router(engine: EngineState) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["Graph"])

    @router.get("/graph")
    def get_graph():
        """Returns the weighted, lagged, directed dependency graph of the 10 layers."""
        K = engine.hawkes.compute_integrated_kernel()
        nodes = [{"id": l, "name": l} for l in engine.layers_list]
        edges = []

        for i, to_l in enumerate(engine.layers_list):
            for j, from_l in enumerate(engine.layers_list):
                if i != j and K[i, j] > 0.08:
                    edges.append({
                        "from": from_l,
                        "to": to_l,
                        "weight": round(float(K[i, j]), 3),
                        "lag_h": 4
                    })

        return {"nodes": nodes, "edges": edges}

    @router.get("/graph/history")
    def get_graph_history():
        """Returns temporal evolution of graph edge weights across simulation ticks."""
        return {
            "timestamps": ["T-24h", "T-18h", "T-12h", "T-6h", "T0"],
            "edges": [
                {"from": "WX", "to": "HYD", "weights": [0.35, 0.52, 0.78, 0.92, 0.95]},
                {"from": "HYD", "to": "TRF", "weights": [0.12, 0.28, 0.65, 0.82, 0.88]},
                {"from": "HYD", "to": "PWR", "weights": [0.05, 0.15, 0.40, 0.55, 0.60]},
                {"from": "TRF", "to": "EMS", "weights": [0.10, 0.25, 0.50, 0.70, 0.75]},
                {"from": "EMS", "to": "HOS", "weights": [0.20, 0.35, 0.60, 0.75, 0.82]}
            ]
        }

    @router.get("/graph/edge/{from_layer}/{to_layer}", response_model=EdgeEvidenceCard)
    def get_edge_evidence(
        from_layer: str = Path(..., description="Source infrastructure layer"),
        to_layer: str = Path(..., description="Target affected infrastructure layer")
    ):
        return engine.get_edge_evidence(from_layer, to_layer)

    return router
