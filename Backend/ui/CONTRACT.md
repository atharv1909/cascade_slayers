# API Contract Specification — The 72-Hour Warning (Cascade_slayers)

This document formalizes the complete data contract between the Python FastAPI backend engine and the user interface.
Switching between DEMO (mock/replay) and LIVE production requires solely updating `window.CONFIG.API_BASE`.

---

## 1. Control Plane Endpoints (Demo Mode)

### `GET /demo/scenarios`
Returns the catalog of selectable hazard scenarios, lead-time semantics, and test variants.
```json
[
  {
    "id": "flood",
    "name": "Monsoon Inundation & Mithi River Drainage Collapse",
    "lead_semantics": "Real lead: 24–72 h from rain forecast + saturation + drainage state",
    "honest_statement": "Rain forecasts + catchment saturation provide physical early warning 24 to 72 hours ahead.",
    "primary_layers": ["WX", "HYD", "TRF", "EMS", "HOS", "PWR", "COM"],
    "critical_condition": "waterlogging_risk_index >= 0.55 for >= 2 h OR roads_accessible_pct <= 40.0"
  }
]
```

### `POST /demo/scenario`
Body: `{"id": "flood", "city": "mumbai", "fault_profile": "F0"}`
Loads the target scenario into the active engine.

### `POST /demo/speed`
Body: `{"x": 2.0}`
Sets the simulation playback multiplier (1x, 2x, 4x).

### `POST /demo/seek`
Body: `{"hour": 68}`
Seeks the simulation clock to the specified hour in the 240-hour episode.

### `POST /demo/pause` & `POST /demo/play`
Pauses or resumes simulation playback.

### `POST /demo/fault`
Body: `{"profile": "F5"}`
Swaps the active sensor fault injection profile (F0 to F5) at the current `as_of`.

---

## 2. Core Risk & Forecast Endpoints

### `GET /v1/risk?as_of={ISO}&zone={id}`
Returns calibrated 4-state risk, cumulative survival probabilities, inverted time-to-critical quantiles, and data confidence.
```json
{
  "as_of": "2026-07-28T20:00:00Z",
  "scenario": "flood",
  "fault_profile": "F0",
  "city": {
    "state": "HIGH_RISK",
    "p_cascade_24h": 0.42,
    "rho": 1.18,
    "confidence": "HIGH"
  },
  "zones": [
    {
      "zone_id": "z04_kurla_w",
      "name": "Kurla West (Bail Bazar)",
      "state": "CRITICAL",
      "confidence": "HIGH",
      "evidence_coverage": 0.94,
      "p": {
        "1": 0.05,
        "3": 0.12,
        "6": 0.28,
        "12": 0.62,
        "24": 0.88,
        "48": 0.94,
        "72": 0.98
      },
      "t_critical": {
        "q10": 4.5,
        "q50": 9.2,
        "q90": 18.0,
        "beyond_72h_p": null
      },
      "event_types": {
        "access_loss": { "p24": 0.85 },
        "power_loss": { "p24": 0.60 }
      },
      "exposure": {
        "population_est": 160000,
        "assets": ["HOS_02_Bhabha_Kurla", "SUB_02_Kurla_Central", "PUMP_02_Kranti_Nagar"],
        "provenance": "MODELLED"
      }
    }
  ]
}
```
*Honesty Rule*: If `p["72"] < 0.50`, `q50` and `q90` are returned as `null`, and `beyond_72h_p` carries the exact probability `P(onset <= 72h)`.

---

## 3. Cascade & Dependency Endpoints

### `GET /v1/cascade?zone={id}|city`
Returns the forward Monte Carlo chain distributions, stage ETAs, branching points, and loops.
```json
{
  "chains": [
    {
      "rank": 1,
      "prob": 0.68,
      "stages": [
        {
          "layer": "WX",
          "event": "Precipitation Peak",
          "eta_h": { "q10": 2.0, "q50": 4.0, "q90": 8.0 }
        },
        {
          "layer": "HYD",
          "event": "Drainage Overflow & Waterlogging",
          "eta_h": { "q10": 4.0, "q50": 8.0, "q90": 14.0 }
        },
        {
          "layer": "TRF",
          "event": "Arterial Road Closure",
          "eta_h": { "q10": 7.0, "q50": 12.0, "q90": 20.0 }
        },
        {
          "layer": "HOS",
          "event": "ICU Bed Saturation",
          "eta_h": { "q10": 12.0, "q50": 22.0, "q90": 40.0 }
        }
      ]
    }
  ],
  "branches": [
    { "at": "HYD", "to": "TRF", "prob": 0.82 },
    { "at": "HYD", "to": "PWR", "prob": 0.45 }
  ],
  "rho": 1.18,
  "loops": [
    { "nodes": ["HOS", "EMS"], "gain": 1.25 }
  ],
  "interaction_gain": 2.35,
  "low_confidence": false
}
```

### `GET /v1/graph/edge/{from}/{to}`
Returns the backing evidence card for a specific dependency link.
```json
{
  "from": "HYD",
  "to": "TRF",
  "weight": 0.82,
  "lag_peak_h": 4,
  "ci": [0.68, 0.96],
  "lr_p": 0.0001,
  "precedes_count": 64,
  "shuffled_baseline": 14,
  "mechanism": "physical",
  "unsupported_flag": false,
  "history": [
    { "t": "T-3h", "w": 0.74 },
    { "t": "T-2h", "w": 0.78 },
    { "t": "T-1h", "w": 0.82 }
  ]
}
```

---

## 4. Intervention & Decision Endpoints

### `POST /v1/intervene`
Body: `{"interventions": ["preposition_pumps", "hospital_backup_generators"], "start_offset_h": 2.0}`
Returns paired counterfactual comparisons isolating treatment impacts:
```json
{
  "baseline": { "p24": 0.88, "rho": 1.18 },
  "plans": [
    {
      "id": "preposition_pumps",
      "name": "Pre-position High-Capacity Pumps",
      "dP": { "24": 0.35, "48": 0.42 },
      "d_eta": { "TRF": 4.2, "HOS": 6.0 },
      "d_rho": 0.32,
      "side_effects": [
        { "description": "Crews diverted away from secondary drainage zones", "layer": "HYD" }
      ],
      "cost": 12500,
      "resources": { "mobile_pumps": 3, "emergency_crews": 2 },
      "deadline_h": 12.0,
      "sensitivity_band": [0.28, 0.46]
    }
  ]
}
```

### `GET /v1/recommend`
Returns the optimal resource-constrained MILP plan and retained emergency reachability:
```json
{
  "selected_interventions": [...],
  "total_cost_usd": 30500,
  "total_risk_reduced_24h": 0.58,
  "unallocated_risk_score": 0.42,
  "retained_access_delta_pp": 26.1,
  "retained_access_people": 221850,
  "next_best_option": { "id": "stage_ambulances", "cost": 6000 }
}
```

---

## 5. Trust, Auditing & Verification

### `GET /v1/ledger/verify`
```json
{
  "ok": true,
  "n_records": 180,
  "first_bad": null,
  "canary_passed": true
}
```

### `GET /v1/canary`
Executes live leakage canary injection test and asserts temporal isolation:
```json
{
  "passed": true,
  "message": "Passed: Future event strictly isolated. Past views at as_of are bit-identical."
}
```

### `GET /v1/sources/reliability`
```json
{
  "sources": [
    {
      "source_id": "hyd_sensor_z04_kurla_w_waterlogging_risk_index",
      "source_type": "sensor",
      "layer": "HYD",
      "reliability": 0.94,
      "staleness_h": 0.1,
      "quarantined": false,
      "history": [0.92, 0.93, 0.94]
    }
  ],
  "quarantined_clusters": []
}
```

---

## 6. Real-Time Ingest & Integration

### `POST /v1/ingest`
Canonical batch event ingest endpoint. Idempotent on `event_id`:
```json
{
  "events": [
    {
      "event_id": "ev_hyd_z04_kurla_w_drain_load_ratio_52",
      "source_id": "cwc_mithi_gauges",
      "source_type": "sensor",
      "layer": "HYD",
      "zone_id": "z04_kurla_w",
      "variable": "drain_load_ratio",
      "value": 1.15,
      "event_time": "2026-07-28T04:00:00Z",
      "ingest_time": "2026-07-28T04:05:00Z",
      "quality": 0.98,
      "meta": {}
    }
  ]
}
```
Response:
```json
{
  "accepted": 1,
  "duplicates": 0,
  "rejected": [],
  "watermark": "2026-07-28T04:05:00Z"
}
```
