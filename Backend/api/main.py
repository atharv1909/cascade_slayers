from __future__ import annotations
import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, PlainTextResponse

from api.engine import EngineState
from api.routes.risk_routes import get_risk_router
from api.routes.cascade_routes import get_cascade_router
from api.routes.graph_routes import get_graph_router
from api.routes.explain_routes import get_explain_router
from api.routes.decide_routes import get_decide_router
from api.routes.sources_routes import get_sources_router
from api.routes.ledger_routes import get_ledger_router
from api.routes.eval_routes import get_eval_router
from api.routes.adapters_routes import get_adapters_router
from api.routes.ingest_routes import get_ingest_router
from api.routes.demo_routes import get_demo_router

# Global Singleton Engine State
engine = EngineState()

# Background ticker task
async def simulation_ticker():
    try:
        while True:
            await asyncio.sleep(1.0)
            if not engine.clock.is_paused:
                # Advance simulation clock by speed multiplier
                steps = int(max(1, engine.clock.speed))
                engine.step_clock(steps)
    except asyncio.CancelledError:
        pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background ticker on startup (disabled during test sweeps)
    task = None
    if not os.environ.get('DISABLE_TICKER'):
        task = asyncio.create_task(simulation_ticker())
    try:
        yield
    finally:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

app = FastAPI(
    title="The 72-Hour Warning (Cascade_slayers)",
    description="Multi-hazard cascading failure early-warning prototype and decision-support engine.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local dashboards and cross-origin tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all domain routers
app.include_router(get_demo_router(engine))
app.include_router(get_risk_router(engine))
app.include_router(get_cascade_router(engine))
app.include_router(get_graph_router(engine))
app.include_router(get_explain_router(engine))
app.include_router(get_decide_router(engine))
app.include_router(get_sources_router(engine))
app.include_router(get_ledger_router(engine))
app.include_router(get_eval_router(engine))
app.include_router(get_adapters_router(engine))
app.include_router(get_ingest_router(engine))

@app.get("/")
def root():
    ui_index = os.path.join(engine.root_dir, "ui", "index.html")
    if os.path.exists(ui_index):
        from fastapi.responses import FileResponse
        return FileResponse(ui_index)
    return {
        "title": "The 72-Hour Warning (Cascade_slayers) API",
        "status": "ONLINE",
        "docs": "/docs",
        "health": "/healthz",
        "scenarios": "/demo/scenarios",
        "risk": "/v1/risk"
    }

# Health and Ops endpoints
@app.get("/healthz")
def healthz():
    return {
        "status": "HEALTHY",
        "scenario": engine.active_scenario,
        "city": engine.active_city,
        "as_of": engine.clock.as_of.isoformat(),
        "paused": engine.clock.is_paused,
        "speed": engine.clock.speed
    }

@app.get("/metrics")
def prometheus_metrics():
    """Prometheus-compatible operational metrics format."""
    lines = [
        "# HELP cascade_slayers_status System operational status",
        "# TYPE cascade_slayers_status gauge",
        "cascade_slayers_status 1",
        "# HELP cascade_slayers_clock_hour Current simulation episode hour",
        "# TYPE cascade_slayers_clock_hour gauge",
        f"cascade_slayers_clock_hour {engine.clock.current_step_h}",
        "# HELP cascade_slayers_events_count Total ingested events count",
        "# TYPE cascade_slayers_events_count counter",
        f"cascade_slayers_events_count {len(engine.store._seen_ids)}",
        "# HELP cascade_slayers_branching_ratio Current cascade reproduction number rho",
        "# TYPE cascade_slayers_branching_ratio gauge",
        f"cascade_slayers_branching_ratio {engine.hawkes.compute_branching_ratio()[0]:.3f}"
    ]
    return PlainTextResponse("\n".join(lines), media_type="text/plain")

# WebSocket Stream for live dashboard push updates
@app.websocket("/v1/stream")
async def websocket_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Push periodic state update
            risk = engine.get_risk_state()
            await websocket.send_json({
                "type": "STATE_UPDATE",
                "as_of": risk.as_of,
                "city_state": risk.city.state.value,
                "rho": risk.city.rho,
                "p_cascade_24h": risk.city.p_cascade_24h,
                "hour": engine.clock.current_step_h
            })
            await asyncio.sleep(2.0)
    except WebSocketDisconnect:
        pass

# Static UI serving if UI files are present
ui_path = os.path.join(engine.root_dir, "ui")
if os.path.exists(ui_path):
    app.mount("/static", StaticFiles(directory=ui_path), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)
