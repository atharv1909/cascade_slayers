# The 72-Hour Warning (PS 2.2) — City Early-Warning & Cascade Decision-Support UI

**The 72-Hour Warning** forecasts how urban hazards (Flood, Heatwave, Power-grid failure, Epidemic surge, Earthquake, Chemical leak, and Compound events) propagate across 10 critical infrastructure layers (`WX`, `HYD`, `TRF`, `PWR`, `EMS`, `HOS`, `HLT`, `AIR`, `SEI`, `COM`) up to 72 hours ahead.

> **Honesty & Validation Notice:** This is a hackathon decision-support prototype calibrated on a simulator, not an operational municipal warning system. Every metric in the UI carries an explicit provenance chip (`OBSERVED · FORECAST · MODELLED · SIMULATED · ASSUMPTION`). For earthquake and chemical leak scenarios, the system does **not** predict the trigger—the 72-hour clock starts at detection (`T0`).

---

## 1. How to Run (100% Offline Static Files)

No build step, bundler, or internet connection is required:

```bash
# 1. (Optional) Regenerate OSM-derived Mithi River Corridor GeoJSON geometry
python3 tools/fetch_city.py

# 2. (Optional) Regenerate seeded graph-diffusion mock fixtures
node ui/mock/generate.mjs

# 3. Serve static files locally
cd ui && python3 -m http.server 8080
```

Then open:
- `http://localhost:8080/index.html` — Unified Landing Page + Command View Dashboard (`DEMO | LIVE` modes, Paper & Dusk themes).

---

## 2. Folder Map

```
├── README.md
├── .gitignore
├── tools/
│   ├── city.json               # Bounding box & metadata for Mithi River Corridor (Mumbai) + Held-out city
│   └── fetch_city.py           # Pulls from OSM Overpass when online, or writes cached Mithi River extract offline
└── ui/
    ├── index.html              # Single-page entry (Landing Page + Command View Dashboard)
    ├── CONTRACT.md             # Canonical API & data contract
    ├── config.local.js.example # Template for untracked local config (API_BASE, GOOGLE_MAPS_KEY)
    ├── app/
    │   ├── api.js              # Single API client module reading window.CONFIG.API_BASE
    │   └── main.js             # Application state, 3D city renderer, ECharts/Cytoscape views, timeline
    ├── data/city/
    │   ├── buildings.geojson   # 512 building footprints with real/approx heights
    │   ├── roads.geojson       # 33 topologically connected arterial/secondary road segments
    │   ├── water.geojson       # Mithi River channel, Vakola Nalla, Safed Pool
    │   ├── drains.geojson      # 10 mapped storm-drain & culvert segments
    │   ├── facilities.geojson  # 14 hospitals, fire/EMS stations, emergency shelters, telecom hubs
    │   ├── substations.geojson # 6 220kV/110kV power substations with feeder zones
    │   ├── zones.geojson       # 20 H3-indexed city zones covering the Mithi corridor
    │   └── landuse.geojson     # District land-use classifications
    ├── mock/
    │   ├── generate.mjs        # Seeded RNG + Dijkstra graph-diffusion mock fixture generator
    │   └── *.json              # Static JSON fixtures matching real API endpoints
    ├── vendor/                 # Offline self-contained vendor shims (MapLibre / ECharts / Cytoscape / Cesium 3D)
    └── fonts/                  # Self-hosted font definitions (Fraunces, Inter, JetBrains Mono)
```

---

## 3. Switching from Mock Data to the Real Backend API

All API calls pass through `ui/app/api.js`, which reads `window.CONFIG.API_BASE` (default `"./mock"`).

To switch to a real backend server:
1. Copy `ui/config.local.js.example` to `ui/config.local.js` (which is ignored by git).
2. Set `window.CONFIG.API_BASE = "http://localhost:8000";` (or your production API URL).
3. Reload the browser—every endpoint listed in `ui/CONTRACT.md` will now query the live API.

---

## 4. Enabling LIVE Mode (Google Photorealistic 3D Tiles & Live Feeds)

By default, the app starts in **DEMO · OFFLINE** mode using local OSM geometry and precomputed simulator replays.

To enable **LIVE** mode (`LIVE VIEW` + `LIVE INPUTS`):
1. Create a Google Cloud project with **Google Maps Platform → Map Tiles API** enabled and billing configured.
2. Copy `ui/config.local.js.example` to `ui/config.local.js` and set:
   ```js
   window.CONFIG = {
     ...window.CONFIG,
     GOOGLE_MAPS_KEY: "YOUR_GOOGLE_MAPS_TILE_API_KEY",
     LIVE_TILE_BUDGET: 250
   };
   ```
3. Or click the **LIVE** switch in the top bar and paste your key in the **Live Config & Quota Guard** dialog (or select **MOCK LIVE** to test the photorealistic hybrid surface, attribution bar, coverage check, and fallback behavior offline).
4. **Google Tile Policy Compliance:**
   - No caching, pre-fetching, or offline storage of Google 3D Tiles.
   - Extruded OSM buildings are automatically hidden in Live View so only our ground-clamped overlays (zones, road state, propagation front, cause→effect trails, facilities, plumes) render over Google's 3D meshes.
   - Dynamic copyright attribution (`asset.copyright`) is aggregated and displayed persistently along the bottom of the viewport.
   - Press **`Shift + D`** at any time for instant demo-day fallback to `DEMO · OFFLINE` mode.
