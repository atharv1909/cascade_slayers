# The 72-Hour Warning (Cascade Slayers 2.2) 🌊⚡🏥

> **Multi-Hazard Cascading Infrastructure Failure Early-Warning & Decision-Support System**  
> Predicting, preventing, and explaining catastrophic urban infrastructure collapses across 72-hour forecast horizons.

---

## 🌟 Overview

When extreme weather or compound disasters strike a modern metropolis, failure does not stay confined to a single sector. A storm surge breaches a drainage canal, waterlogging road corridors, cutting ambulance routing, tripping transmission substations, and knocking emergency hospital capacity into saturation.

**The 72-Hour Warning** provides emergency managers, municipal civil defense authorities, and critical utility operators with an integrated early-warning dashboard and predictive physical AI backend.

### Core Capabilities
- **Landing Showcase & Live Command Center**: Interactive luxury peach/obsidian landing page (UI/landing.html) and live operations cockpit (UI/index.html) with real-time multi-hazard telemetry, 3D orthographic projection, and dynamic timeline playback.
- **Embedded Voiceflow AI Assistant**: Intelligent multi-hazard incident advisory copilot integrated seamlessly at the bottom-right of both the landing page and dashboard.

- **Monotone Multi-Horizon Risk Estimation**: Predicts cumulative failure probabilities across $[1\text{h}, 3\text{h}, 6\text{h}, 12\text{h}, 24\text{h}, 48\text{h}, 72\text{h}]$ using LightGBM with monotonic constraints ($P(1) \le P(3) \le \dots \le P(72)$) calibrated with isotonic regression.
- **Cross-Layer Hawkes Cascading Process**: Computes mutual excitation intensity between infrastructure domains (Weather $\to$ Hydrology $\to$ Traffic $\to$ Power $\to$ EMS $\to$ Hospitals $\to$ Comms), estimating the dynamic reproduction number $\rho$ (super-critical cascade flag $\rho > 1$).
- **Conformal Time-to-Critical Quantiles**: Inverts the cumulative failure CDF to provide honest $[q_{10}, q_{50}, q_{90}]$ interval forecasts. If $P(72\text{h}) < 0.5$, it outputs `"Beyond 72h"` rather than fabricating misleading timestamps (Rule Zero).
- **Multi-Hazard Digital Twin Simulator**: 8 realistic crisis scenarios (Monsoon Inundation, Extreme Heat & Grid Strain, Earthquake & ETAS Aftershocks, Chlorine Hazmat Release, Epidemic Surge, Compound Multi-Hazard A/B, and Held-Out Generalization City).
- **Adversarial Fault Profiles**: Robust State Estimation resilient against 6 sensor failure modes ($F_0$: Pristine, $F_1$: Random Dropout, $F_2$: Burst Outage, $F_3$: Sensor Drift, $F_4$: Stuck Sensor, $F_5$: Malicious Spoofer).
- **Monsoon Slate 3D Command Center**: Ultra-clean, clutter-free dark slate aesthetic (`#0B0F14`) with molten amber accents, interactive 3D orthographic projection of the urban corridor, cross-layer dependency graphs, and intervention sandboxes.

---

## 🏛️ Architecture & Project Layout

```text
Cascade/
├── Backend/                        # FastAPI AI & Simulation Engine
│   ├── adapters/                   # Real-time USGS & Open-Meteo API connectors
│   ├── api/                        # REST routes (/v1/risk, /v1/cascade, /v1/graph, /v1/decide, ...)
│   ├── cascade/                    # Hawkes process & ETAS seismic point process models
│   ├── configs/                    # City topology & scenario plugin definitions
│   ├── decide/                     # Resource allocation & intervention optimization engine
│   ├── eval/                       # Brier scoring, reliability diagrams & audit ledger
│   ├── harness/                    # Fault injection & evaluation harness
│   ├── risk/                       # LightGBM multi-horizon hazard model & calibrators
│   ├── runs/                       # Generated multi-hazard episode logs & trained model weights
│   ├── sim/                        # Physics layers (Hydrology, Traffic, Power, EMS, Hospitals)
│   ├── state/                      # Truth discovery & robust Kalman state estimation
│   ├── tests/                      # Pytest suite (14/14 passing)
│   ├── training code/              # Kaggle/Jupyter training notebooks
│   ├── ui/                         # Built-in static UI assets
│   ├── Dockerfile                  # Containerized deployment
│   ├── Procfile                    # Web service definition
│   ├── render.yaml                 # Render cloud configuration
│   └── requirements.txt            # Python dependencies
├── UI/                             # Frontend Dashboard
│   ├── index.html                  # Inlined standalone single-page application
│   ├── vercel.json                 # Vercel deployment configuration
│   └── UI_UPGRADE_README.md        # UI design specification & guidelines
├── tools/                          # Automation & Assembly Pipeline
│   ├── assemble_ui.py              # Bundles city GeoJSON, mock events & UI engine
│   ├── ui_core.js                  # UI state machine, canvas 3D renderer & live API client
│   └── ui_head.html                # CSS styles, design tokens & header structure
├── 72H_WARNING_BLUEPRINT.md        # Comprehensive system specification
├── vercel.json                     # Root Vercel routing
├── render.yaml                     # Root Render infrastructure spec
└── README.md
```

---

## 🚀 Quickstart Guide

### 1. Running Backend Locally

```bash
cd Backend
python -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Run FastAPI server on port 8000
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```
- Interactive Swagger docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/healthz`
- Risk endpoint: `http://localhost:8000/v1/risk`
- Embedded UI: `http://localhost:8000/`

### 2. Running Frontend Locally

Open `UI/index.html` directly in any modern browser, or serve it with any static server:
```bash
# Using Python
python -m http.server 3000 --directory UI

# Or using Node / Vercel CLI
npx serve UI
```

### 3. Running Verification Suite

```bash
cd Backend
pytest tests/ -v
```
All **14/14 test cases pass**, validating API contracts, time-to-critical monotonicity, fault injection, and canary integrity audits.

---

## ☁️ Deployment

### Deploying Backend on Render
1. Connect this repository to [Render](https://render.com).
2. Render will automatically detect [`render.yaml`](render.yaml) or point the service to `Backend`:
   - **Environment**: Python 3.11
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`

### Deploying Frontend on Vercel
1. Connect this repository to [Vercel](https://vercel.com).
2. Vercel automatically uses [`vercel.json`](vercel.json):
   - **Root Directory**: `UI` (or leave default root)
   - **Output Directory**: `.`
   - Pure client-side zero-build single-page web app with sub-millisecond CDN delivery.

---

## 📊 Evaluation & Verification Metrics

- **Multi-Horizon Monotonicity**: $100\%$ mathematical compliance ($P(1) \le P(3) \le \dots \le P(72)$).
- **Brier Score**: $\le 0.12$ across all evaluated crisis episodes.
- **Conformal Coverage**: $90\%$ empirical coverage on held-out test episodes.
- **Inference Latency**: Sub-second full city-wide risk inference across 20+ metropolitan zones.

---

## 👥 Authors & Team
- **Repository**: [bhalerao-aditya007/Cascade_slayers_2.2](https://github.com/bhalerao-aditya007/Cascade_slayers_2.2)
- Built for the Cascade Slayers Hackathon 2026.
