# API & Data Contract — "The 72-Hour Warning" (PS 2.2)

This file defines the canonical HTTP/JSON contract between the frontend (`ui/app/api.js`) and the backend or static mock fixtures (`ui/mock/`).

Switching from mock mode to the live backend requires changing **only** `window.CONFIG.API_BASE` (default `"./mock"`, or `"http://localhost:8000"` in `ui/config.local.js`).

---

## 1. Runtime Configuration (`window.CONFIG`)

```js
window.CONFIG = {
  API_BASE: "./mock",                // Switch to real API base URL when backend is live
  DEFAULT_MODE: "DEMO",              // "DEMO" (offline OSM + replay) | "LIVE"
  GOOGLE_MAPS_KEY: "",               // Optional: set in untracked ui/config.local.js for Google 3D Tiles
  LIVE_TILE_BUDGET: 250,             // Max tile requests per session before automatic fallback
  DEFAULT_THEME: "paper"             // "paper" (light warm linen) | "dusk" (warm charcoal)
};
```

---

## 2. Provenance & Honesty Invariants

Every metric rendered in the UI carries an explicit `provenance` tag from:
- `OBSERVED` — Raw sensor or telemetry reading (or live feed in LIVE INPUTS mode)
- `FORECAST` — External meteorological / upstream forecast input
- `MODELLED` — Output of the Chronos-2 / LightGBM / Hawkes dependency model
- `SIMULATED` — Simulator-calibrated replay or synthetic counterfactual
- `ASSUMPTION` — Intervention efficacy parameter or resource transfer assumption

**Hard Invariants:**
1. If `t_critical.beyond_72h_p !== null` (i.e. `P(<=72h) < 0.90`), the UI **never** fabricates a median `q50`; it renders `"beyond 72 h, P = x"`.
2. Earthquake (`quake_fault`) and Chemical leak (`chem_plume`) have `clock_semantics: "DETECTION_LOCKED"`. The UI explicitly announces that triggers are not predicted and the 72h clock starts at T0 detection.
3. No water-depth values (cm/m) or "lives saved" / casualty counts are ever emitted or displayed. Flood uses a dimensionless `waterlogging_risk_index` (0.00–1.00) and `retained_emergency_access` (% points + reachable population delta, tagged `MODELLED`).

---

## 3. Endpoints & Payload Shapes

### `GET /demo/scenarios`
Returns the scenario catalogue including the 6 core hazards, the Compound scenario, the Held-Out City (`never_tuned_on: true`), and the Regime Drift scenario (`drift_mode: true`).

### `POST /demo/scenario` · `POST /demo/speed` · `POST /demo/seek` · `POST /demo/pause` · `POST /demo/play` · `POST /demo/fault`
State control endpoints for the global 240h simulation clock (`0..240h`, where `0..48h` is warm-up) and fault injection profile (`F0..F5`).

### `GET /v1/risk?as_of=&zone=`
Returns city-level risk state, zone-level risk states across the 20 H3 hexagons, and **per-asset propagation state** (`onset_h`, `severity`, `parents`, `children`) computed over the real city infrastructure graph:

```json
{
  "as_of": "2026-07-18T16:00:00Z",
  "sim_hour": 64,
  "scenario": "flood_mithi",
  "fault_profile": "F0",
  "provenance": "SIMULATED",
  "city": {
    "state": "HIGH_RISK",
    "p_cascade_24h": 0.89,
    "rho": 1.38,
    "confidence": "HIGH"
  },
  "zones": [
    {
      "zone_id": "88608b4c07fffff",
      "zone_code": "Z04",
      "name": "Dharavi Cross Rd & T-Junction",
      "state": "CRITICAL",
      "confidence": "HIGH",
      "confidence_reason": "Multi-sensor agreement across HYD + TRF",
      "evidence_coverage": 0.91,
      "p": { "1": 0.21, "3": 0.36, "6": 0.52, "12": 0.68, "24": 0.82, "48": 0.90, "72": 0.96 },
      "t_critical": { "q10": 6.5, "q50": 11.0, "q90": 17.5, "beyond_72h_p": null },
      "event_types": {
        "drain_overload": { "p24": 0.84 },
        "access_loss": { "p24": 0.76 },
        "substation_trip": { "p24": 0.59 },
        "hospital_strain": { "p24": 0.71 }
      },
      "exposure": {
        "population_est": 112000,
        "assets": ["DRN-08", "RD-04", "FAC-HOS-06", "FAC-EMS-02", "SUB-01"],
        "provenance": "MODELLED"
      }
    }
  ],
  "assets": {
    "DRN-06": {
      "asset_id": "DRN-06",
      "name": "BKC Mithi Retaining Channel",
      "layer": "HYD",
      "zone_code": "Z09",
      "onset_h": 57.0,
      "onset_q10": 53.5,
      "onset_q90": 61.5,
      "recommended_onset_h": 71.5,
      "severity": 3,
      "parents": [{ "id": "DRN-07", "lag_h": 2.5, "weight": 0.76, "edge_key": "HYD->HYD" }],
      "children": [{ "id": "RD-13", "lag_h": 3.5, "weight": 0.82, "edge_key": "HYD->TRF" }],
      "provenance": "SIMULATED"
    }
  }
}
```

### `GET /v1/cascade?zone=|city`
```json
{
  "chains": [
    {
      "rank": 1,
      "prob": 0.64,
      "stages": [
        { "layer": "HYD", "event": "Mithi & Bail Bazaar Culvert Overload", "zone_code": "Z14", "eta_h": { "q10": 4.5, "q50": 7.0, "q90": 10.0 } }
      ]
    }
  ],
  "branches": [{ "at": "HYD · Drain Overload", "to": "PWR · Substation Inundation Trip", "prob": 0.48 }],
  "rho": 1.38,
  "loops": [{ "nodes": ["PWR", "HYD"], "gain": 1.24 }],
  "interaction_gain": null,
  "low_confidence": false
}
```

### `GET /v1/graph` · `GET /v1/graph/history` · `GET /v1/graph/edge/{i}/{j}`
```json
{
  "from": "HYD",
  "to": "TRF",
  "weight": 0.84,
  "lag_peak_h": 4.0,
  "ci": [2.5, 6.0],
  "lr_p": 0.00018,
  "precedes_count": 38,
  "shuffled_baseline": 5.4,
  "mechanism": "physical",
  "unsupported_flag": false,
  "history": [{ "t": "T-48h", "w": 0.69 }, { "t": "T0h", "w": 0.84 }]
}
```

### `GET /v1/explain?zone=&layer=&as_of=`
Returns signed Shapley/driver attributions per layer, upstream parent ranking, data health badge, and a timestamped **cascade receipt** (`inputs -> rule -> affected_items -> impact`).

### `POST /v1/intervene` · `GET /v1/recommend` · `GET /v1/access`
```json
{
  "baseline": { "p24": 0.89, "rho": 1.38, "retained_access_pct": 61.4 },
  "plans": [
    {
      "id": "plan_recommended",
      "dP": { "1": -0.02, "3": -0.06, "6": -0.14, "12": -0.22, "24": -0.29, "48": -0.31, "72": -0.28 },
      "d_eta": { "HYD": 6.5, "TRF": 11.0, "PWR": 14.5, "HOS": 18.0 },
      "d_rho": -0.46,
      "side_effects": ["LBS Marg Northbound contraflow adds +18 min civilian congestion in Z10/Z11"],
      "cost": 68,
      "resources": { "pumps": 14, "crews": 10, "ambulances": 18, "generators": 8, "shelter_seats": 1600 },
      "deadline_h": 5.5,
      "sensitivity_band": [-0.35, -0.21]
    }
  ]
}
```

### `GET /v1/sources/reliability` · `GET /v1/ledger/verify` · `GET /v1/canary` · `GET /v1/metrics/eval` · `GET /v1/adapters` · `POST /v1/ingest` · `GET /v1/risk.geojson` · `GET /v1/alerts.cap`
Full telemetry reliability tables, SHA-256 hash-chained forecast ledger verification, temporal data-leakage canary check, calibration / lead-time / fault-sweep evaluation metrics, live adapter statuses (`REPLAY | CACHED | LIVE`), GeoJSON export, and OASIS CAP v1.2 XML alert feed.
