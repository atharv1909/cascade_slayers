from __future__ import annotations
from typing import Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Body, Response
from api.engine import EngineState
from api.routes.cap import generate_cap_alert_xml
from api.routes.geojson import generate_risk_geojson

class LoadScenarioRequest(BaseModel):
    id: str = "flood"
    city: str = "mumbai"
    fault_profile: str = "F0"

class SpeedRequest(BaseModel):
    x: float = 1.0

class SeekRequest(BaseModel):
    as_of: Optional[str] = None
    hour: Optional[int] = None

class FaultRequest(BaseModel):
    profile: str = "F0"

def get_demo_router(engine: EngineState) -> APIRouter:
    router = APIRouter(tags=["Demo Control Plane"])

    @router.get("/demo/scenarios")
    def get_scenarios():
        """Returns catalog of all 6 hazard scenarios, compound scenarios, held-out city, and drift."""
        return [
            {
                "id": "flood",
                "name": "Monsoon Inundation & Mithi River Drainage Collapse",
                "lead_semantics": "Real lead: 24–72 h from rain forecast + saturation + drainage state",
                "honest_statement": "Rain forecasts + saturation provide 24-72h lead. System forecasts drainage backup, road closures, hospital cutoff.",
                "primary_layers": ["WX", "HYD", "TRF", "EMS", "HOS", "PWR", "COM"],
                "critical_condition": "waterlogging_risk_index >= 0.55 for >= 2 h OR roads_accessible_pct <= 40.0"
            },
            {
                "id": "heat",
                "name": "Extreme Humid Heat-Dome & Grid Stress",
                "lead_semantics": "Real lead: 3–5 days from temperature/humidity forecast; load and hospital effects lag",
                "honest_statement": "Weather forecast gives 3-5 days lead; system forecasts lagging substation overload and heatstroke ED arrivals.",
                "primary_layers": ["WX", "PWR", "HLT", "HOS", "COM"],
                "critical_condition": "wbgt_c >= 32.0 for >= 3 h AND ed_arrivals_per_h >= 28.0"
            },
            {
                "id": "grid",
                "name": "Cascading Power Grid & Feeder Infrastructure Failure",
                "lead_semantics": "Real lead: 12–72 h if weather/load-driven; fault-triggered starts at first fault",
                "honest_statement": "Weather/load driven gives 12-72h. Fault-triggered starts at first trip; system forecasts cascade.",
                "primary_layers": ["PWR", "TRF", "HYD", "HOS", "COM"],
                "critical_condition": "customers_out_pct >= 35.0 for >= 2 h"
            },
            {
                "id": "epidemic",
                "name": "Syndromic Epidemic Surge & Critical Care Overrun",
                "lead_semantics": "Real lead: days for hospital strain (ED/syndromic signals lead occupancy); we forecast the surge, not the pathogen",
                "honest_statement": "Syndromic/ED signals lead hospital occupancy by days; system forecasts the surge, not the pathogen.",
                "primary_layers": ["HLT", "HOS", "EMS", "COM"],
                "critical_condition": "icu_occupancy_pct >= 90.0 OR bed_occupancy_pct >= 95.0"
            },
            {
                "id": "quake",
                "name": "Earthquake Mainshock & Structural Secondary Cascades",
                "lead_semantics": "No precursors. Clock starts at mainshock detection. 72 h covers aftershocks + secondary cascade.",
                "honest_statement": "No earthquake precursors. Clock starts at detection; system forecasts aftershocks (ETAS) and infrastructure cascade.",
                "primary_layers": ["SEI", "PWR", "TRF", "AIR", "HOS", "EMS"],
                "critical_condition": "shaking_intensity_mmi >= 7.0 OR damage_index >= 0.40"
            },
            {
                "id": "chem",
                "name": "Industrial Point-Release Toxic Gas Plume",
                "lead_semantics": "No precursors. Clock starts at first sensor/report. We forecast plume and downstream cascade.",
                "honest_statement": "No release precursors. Clock starts at first sensor/report; system forecasts plume footprint and downstream cascade.",
                "primary_layers": ["AIR", "TRF", "HOS", "EMS", "COM"],
                "critical_condition": "concentration_index >= 2.5 for >= 1 h in populated zone"
            },
            {
                "id": "compound_a",
                "name": "Compound Disruption: Flood × Grid Failure × Hospital Saturation",
                "lead_semantics": "Two cascades share a bottleneck",
                "honest_statement": "Two cascades interact with interaction_gain > 1.0; shared hospital power and ambulance transit bottlenecks.",
                "primary_layers": ["WX", "HYD", "PWR", "TRF", "EMS", "HOS", "COM"],
                "critical_condition": ">= 3 layers critical within 12 h window across >= 2 coupled zones"
            },
            {
                "id": "compound_b",
                "name": "Compound Disruption: Earthquake Rupture → Toxic Gas Leakage & Grid Severance",
                "lead_semantics": "Tectonic trigger induces multiple simultaneous cascades",
                "honest_statement": "Quake triggers substation trips, industrial gas pipeline shears, and road collapses.",
                "primary_layers": ["SEI", "PWR", "AIR", "TRF", "HOS", "EMS"],
                "critical_condition": ">= 3 layers critical within 12 h window"
            },
            {
                "id": "heldout_city",
                "name": "Held-Out City Benchmark (Pune Mutha Basin)",
                "lead_semantics": "Generalization test on completely unseen topology (Never Tuned On)",
                "honest_statement": "Evaluates cold-start generalization on 16 unseen zones with different elevation and drainage parameters.",
                "primary_layers": ["WX", "HYD", "TRF", "PWR", "EMS", "HOS"],
                "critical_condition": "waterlogging_risk_index >= 0.55"
            }
        ]

    @router.post("/demo/scenario")
    def post_scenario(body: LoadScenarioRequest = Body(...)):
        engine.load_scenario(body.id, body.city, body.fault_profile)
        return {
            "status": "LOADED",
            "scenario": engine.active_scenario,
            "city": engine.active_city,
            "fault_profile": engine.active_fault_profile,
            "as_of": engine.clock.as_of.isoformat()
        }

    @router.post("/demo/speed")
    def post_speed(body: SpeedRequest = Body(...)):
        engine.clock.set_speed(body.x)
        return {"status": "UPDATED", "speed": engine.clock.speed}

    @router.post("/demo/seek")
    def post_seek(body: SeekRequest = Body(...)):
        target_h = body.hour if body.hour is not None else 48
        engine.seek_clock(target_h)
        return {"status": "SEEKED", "hour": engine.clock.current_step_h, "as_of": engine.clock.as_of.isoformat()}

    @router.post("/demo/pause")
    def post_pause():
        engine.clock.pause()
        return {"status": "PAUSED"}

    @router.post("/demo/play")
    def post_play():
        engine.clock.play()
        return {"status": "PLAYING"}

    @router.post("/demo/fault")
    def post_fault(body: FaultRequest = Body(...)):
        engine.load_scenario(engine.active_scenario, engine.active_city, body.profile)
        return {"status": "FAULT_PROFILE_APPLIED", "fault_profile": engine.active_fault_profile}

    @router.post("/demo/drift")
    def post_drift(kind: str = "drain_blockage"):
        """Injects mid-episode concept drift into the simulation."""
        alarm = {
            "type": "INJECTED_DRIFT",
            "kind": kind,
            "hour": engine.clock.current_step_h,
            "message": "Drainage pump failure injected. HYD->TRF coupling edge strengthening."
        }
        engine.drift.drift_alarms.append(alarm)
        return {"status": "DRIFT_INJECTED", "alarm": alarm}

    # Integration endpoints
    @router.get("/v1/alerts.cap")
    def get_alerts_cap():
        """Returns standard CAP v1.2 XML document for active critical zone."""
        xml_str = generate_cap_alert_xml(
            alert_id="001",
            zone_id="z04_kurla_w",
            zone_name="Kurla West (Bail Bazar)",
            risk_state="CRITICAL",
            headline="Severe Arterial Inundation & Emergency Access Loss Expected",
            description="Mithi river overflow coupled with CST Road blockage severing emergency ambulance access to KB Bhabha Hospital.",
            instruction="Deploy mobile drainage pumps immediately and initiate SCLR traffic detour. Avoid low-lying Bail Bazar corridor.",
            as_of=engine.clock.as_of
        )
        return Response(content=xml_str, media_type="application/xml")

    @router.get("/v1/risk.geojson")
    def get_risk_geojson_endpoint():
        """Returns GeoJSON FeatureCollection of all active zones with risk state properties."""
        risk_resp = engine.get_risk_state()
        zones_data = []
        zones_cfg = engine.get_active_zones()
        zone_map = {z["id"]: z for z in zones_cfg}

        for zr in risk_resp.zones:
            cfg = zone_map.get(zr.zone_id, {})
            zones_data.append({
                "zone_id": zr.zone_id,
                "name": cfg.get("name", zr.zone_id),
                "lat": cfg.get("lat", 19.06),
                "lon": cfg.get("lon", 72.86),
                "state": zr.state.value,
                "confidence": zr.confidence.value,
                "evidence_coverage": zr.evidence_coverage,
                "p": zr.p,
                "elevation_m": cfg.get("elevation_m", 5.0),
                "population": zr.exposure.population_est
            })

        return generate_risk_geojson(zones_data)

    return router
