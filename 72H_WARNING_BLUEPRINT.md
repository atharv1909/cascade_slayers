# THE 72-HOUR WARNING — Build Blueprint
**Constraints:** 24 h total build · ≤10 h Kaggle T4 training · demo-first · 6 hazards · one stack
**Rule zero:** the demo is the product. Every feature must be visible on screen or provable through an endpoint. If a judge cannot see it or call it, do not build it.

---

## 1. Scope contract

| Item | Decision |
|---|---|
| Hazards | Flood/water disaster · Extreme heat/heatwave · Epidemic/pandemic surge · Infrastructure & power-grid failure · Earthquake · Chemical gas leak |
| Urban layers (10 nodes per zone) | WX weather · HYD drainage/water · TRF traffic & road access · PWR power · EMS emergency response · HOS hospital · HLT health surveillance · AIR air/gas · SEI seismic/structural · COM comms & citizen reports |
| Zones | ~20 H3 hex cells (anchor city), ~16 (held-out city) |
| Time step | 1 hour. Episode = 10 days (240 h), first 48 h warm-up |
| Horizons | 1, 3, 6, 12, 24, 48, 72 h |
| Risk states | NORMAL · WATCH · HIGH RISK · CRITICAL — per zone and city-wide |
| Deliverable | Simulated demo that runs through the **same ingest → forecast → cascade → decision code path** a production deployment would use |

### 1.1 Lead-time semantics (state this openly in the demo)

"72 hours before" is physically meaningful only for some hazards. Pretending otherwise is the fastest way to lose credibility with a technical judge.

| Hazard | Real 72 h lead? | What "warning" means in this system |
|---|---|---|
| Flood | Yes | Rain forecast + saturation + drainage state give 24–72 h |
| Heatwave | Yes | Temperature/humidity forecast gives 3–5 days; load and hospital effects lag |
| Epidemic surge | Yes (for hospital strain) | Syndromic/ED signals lead hospital occupancy by days; system forecasts the surge, not the pathogen |
| Grid failure | Partial | Weather/load-driven: 12–72 h. Fault-triggered: starts at first fault; system forecasts the cascade |
| Earthquake | **No precursors** | Clock starts at mainshock detection. 72 h covers aftershock hazard (ETAS) and secondary cascade (grid, roads, hospitals, gas) |
| Chemical leak | **No precursors** | Clock starts at first sensor/report. System forecasts plume footprint and downstream cascade over hours |

Say: *"For quake and chemical release we do not claim to predict the trigger. We forecast the cascade the trigger starts."*

### 1.2 Data sufficiency verdict

**Short answer: you do not have enough real data to train or validate this on real cascades. You have enough to build and demo it credibly if you use a calibrated simulator, and you must say so.**

| Needed | Available on Kaggle / open? | Consequence |
|---|---|---|
| Aligned multi-layer, sub-daily streams for one city | No | Cannot learn cross-layer dependencies from real data alone |
| Ground-truth cascade stage labels | No (nowhere) | Cannot supervise stage timing on real data |
| Per-hazard single-layer series (rain, temp, traffic, load, calls, cases, quakes, AQ) | Yes, mostly daily/hourly | Use to **calibrate** simulator marginals and dynamics |
| Real power-outage time series | Yes, but outside Kaggle (EAGLE-I, ORNL/figshare, 15-min, US counties) | Use for outage duration/restoration statistics |
| Real earthquake sequences | Yes (USGS catalog) | Real ETAS fit + real aftershock replay |
| Real epidemic curves | Yes (COVID sets) | Real SEIR/Rt replay |
| Chemical release incidents | Weak | Physics (Gaussian puff) only; say so |

**Strategy:** (1) build a mechanistic **city digital twin** whose coupling structure is *hidden from the model*; (2) calibrate each layer's marginals/dynamics to real Kaggle/open data; (3) generate thousands of episodes; (4) train on simulated episodes, evaluate on unseen episodes **and an unseen city**; (5) add one **real replay per hazard where real data exists** (quake, epidemic, weather, outages). Ground truth being known is a *feature*: you can score dependency discovery and counterfactual accuracy, which no real dataset allows.

**Inverse-crime guard:** if the simulator uses the same math as the model (Hawkes in, Hawkes out), recovery is trivially perfect and judges will see through it. The simulator must use *different* functional forms (queues, saturation, thresholds, SCS-CN runoff, SEIR, Gaussian puff, ETAS). Disclose that the model is not given the simulator's equations.

---

## 2. The one stack

| Concern | Choice | Why (research / practical) | GPU? |
|---|---|---|---|
| Streaming/replay | Event-sourced Parquet log + DuckDB as-of queries + in-process asyncio queue | Strict future isolation is gradable; no Kafka needed | No |
| Per-layer forecasting | **Chronos-2** (120M, `amazon/chronos-2`; 28M `autogluon/chronos-2-small` for CPU) zero-shot with known-future covariates | Verified from model card: encoder-only, Apache-2.0, native multivariate + past/known-future covariates, group attention for cross-series learning, quantile outputs, CPU/GPU, >300 series/s on A10G. **No static covariates** — keep statics in the GBM | Yes (inference) |
| Calibrated multi-horizon risk | **LightGBM** with `horizon` as a feature + monotone constraint (+1) so P(event ≤ h) never decreases with h | Gives a valid CDF → time-to-critical quantiles by inversion; fast on CPU | No |
| Dependency discovery + cascade engine | **Discrete-time multivariate Hawkes (point-process GLM)** in PyTorch, non-negative L1, low-rank lag basis, online SGD with forgetting | Hawkes kernels = lagged influence graph + branching ratio (explainable); Xu et al. ICML'16 link Hawkes to Granger causality | Optional |
| Seismic | **ETAS** (Omori-Utsu + Gutenberg-Richter), MLE in SciPy | ETAS is a Hawkes process — same engine, same explainability | No |
| Uncertainty | Split-conformal + **CQR** + **Adaptive Conformal Inference** (Gibbs & Candès 2021) + **Mondrian bins by data-quality** | Valid coverage, online, degrades gracefully with bad data | No |
| Adversity | Truth discovery (CRH-style reliability, Li et al. 2014) + Beta-Bernoulli reporter trust + Hampel/robust filters | Handles bad sensors and fake reports without labels | No |
| Online learning | **River** (ADWIN / Page-Hinkley drift, online linear corrector) + Hawkes SGD + ACI | Real online updates, no retrain-from-scratch | No |
| Decisions | Monte-Carlo counterfactual on fitted cascade model with **common random numbers** + MILP (`scipy.optimize.milp`) under resource limits + cost-loss thresholds | Defensible, fast, interactive | No |
| Explainability | TreeSHAP (GBM) + exact Hawkes parent attribution + per-edge evidence cards | Two complementary, verifiable explanations | No |
| API | **FastAPI + Pydantic v2 + SSE/WebSocket** | The endpoints *are* the production proof | No |
| UI | Single-page app, no build step: **MapLibre GL JS + ECharts + Cytoscape.js** | Smooth streaming and time-warp; Streamlit chokes on this | No |
| Tracking | Git + Parquet run logs | MLflow is time you do not have | No |

**Explicitly rejected** (do not add them mid-build): Kafka, Spark, RL, neural TPPs (THP/SAHP), Gumbel-Max counterfactual TPP, Tigramite in the online loop, SWMM in the loop, LLM-generated probabilities, MLflow, microservices, Kubernetes.

Optional offline extras (only if ahead of schedule): PCMCI+ (Runge et al. 2019) once per hazard on hourly aggregates as a cross-check of the Hawkes graph; `pandapower` DC power-flow N-1 cascade for a 39-bus grid to ground the grid plugin.

---

## 3. Architecture

```
 [Simulator / Replay / Live adapters]
        │  canonical events (event_time, ingest_time, source, zone, var, value, quality)
        ▼
 L0  HARNESS  ── fault injector ── ingest API ── event log (Parquet) ── as-of store (DuckDB)
        │                                        └── hash-chained forecast ledger
        ▼
 L1  STATE ESTIMATOR  ── truth discovery / source reliability ── robust fusion ── data-quality score
        ▼
 L2  FORECAST  ── Chronos-2 per-layer quantile forecasts (+ weather-forecast covariates)
        ▼
 L3  EVENTS  ── severity ladder (0–3) per layer/zone ── typed onset events
        ▼
 L4  CASCADE ENGINE  ── online Hawkes graph (influence, lags, branching ρ, loops)
        │               ── forward Monte-Carlo (chains, joint timing, compound interaction)
        ▼
 L5  RISK HEAD  ── LightGBM multi-horizon CDFs ── isotonic calibration ── CQR+ACI+Mondrian
        │            ── 4-state mapping with hysteresis (zone + city)
        ▼
 L6  DECISIONS  ── intervention catalog ── counterfactual MC (CRN) ── MILP allocation ── deadline clocks
        ▼
 L7  SERVE  ── REST/SSE/WS ── CAP alerts ── GeoJSON ── UI ── metrics ── ledger verify
```

Data flow rule: **nothing downstream of L0 may read anything with `ingest_time > as_of`.** Enforce in one function (`store.view(as_of)`); no module gets a raw handle to the full log.

---

## 4. City digital twin and simulator

### 4.1 Shared twin
- **Geometry:** pick one real anchor city and one real held-out city (different climate/topography). Zones = H3 cells over the bbox (`h3` v4). Elevation from a cached SRTM/Open-Elevation pull; population from WorldPop or synthetic density.
- **Graphs:** zone adjacency (spillover), drainage flow graph (downhill), feeder graph (zone → substation → grid), road graph (coarse: zone-to-zone edges with capacity), hospital catchments.
- **Assets:** hospitals (beds, ICU, generator hours), substations (rating), pumping stations, shelters, one chemical plant, ambulance depots.
- **Held-out city** has different elevation profile, drain capacity, grid topology, hospital density, rainfall/heat regime. **Lock it**: generate its episodes once with a separate seed, do not look at them until final evaluation.

### 4.2 Layer mechanics (must NOT be Hawkes-shaped)

| Layer | Mechanism | Observed variables |
|---|---|---|
| WX | Seasonal + diurnal baseline + storm/heat-dome event generator. **Issues forecasts every 6 h with lead-dependent error growth** (σ rises roughly linearly with lead) — never expose true future | rain mm/h, temp, RH, wind speed/dir, WBGT (from Stull wet-bulb approx.) |
| HYD | SCS-Curve-Number runoff → storage per zone → drain capacity `C_z` (random blockage, pump multiplier) → overflow routed downhill | drain load ratio, river/canal level, waterlogging depth |
| TRF | `speed = free × (1−σ(depth−d0)) × (1−signal_outage×a) × demand(hour)`; road closures from depth, quake, plume | speed index, % roads accessible |
| PWR | Demand = base × diurnal × (1+β·max(0,T−28)); overload hazard rises with load/rating and flood depth at substation; outage durations lognormal; restoration limited by crew queue | load ratio, substation loading, % customers out |
| EMS | Calls ~ Poisson(base(hour) × multipliers from weather/heat/incident); response = base + distance/TRF speed + M/M/c queue delay | call rate, response time, units unavailable |
| HOS | M/M/c/K queue with LOS; arrivals from EMS + heat + epidemic + casualties; diversion above ~90% occupancy shifts load to neighbors; generator failure if outage exceeds backup hours | bed occupancy, ED arrivals, boarding, supply days |
| HLT | Metapopulation SEIR over mobility graph; ED syndromic visits = ρ·I with reporting delay; case counts delayed 2–5 days | ED syndromic count, case count, Rt |
| AIR | Gaussian **puff** model (time-varying wind, Pasquill stability) from point source; sensors with noise and drift | concentration index per zone, AQI |
| SEI | Mainshock magnitude/location → ETAS aftershocks → shaking by a single documented GMPE → lognormal fragility → damaged-structure index; triggers PWR trips, TRF blockages, gas-line release → AIR, casualties → HOS | shaking intensity, aftershock rate, damage index |
| COM | Network load ∝ calls + reports; fails if power out > battery hours; citizen reports ~ Poisson(adoption × true severity) + **false-report processes** (spam bursts, geo-spoof) | load, report rate, report text class |

Hidden ground-truth coupling matrix `G` (for scoring only) is the union of these mechanisms; save it with each episode (`G_true.parquet`: from, to, lag range, strength).

### 4.3 Scenario families (per-hazard plugins)

Each plugin = one YAML + ≤100 lines of custom code. Core engine is shared. Thin plugins are the single biggest time-saver in 24 h.

| Plugin | Trigger generator | Critical event (config thresholds) | Chain the model must discover | Priority |
|---|---|---|---|---|
| **flood** | Multi-day rain event, intensity/duration random; antecedent saturation | Waterlogging ≥ X cm in ≥ k% of zone ≥ 2 h OR key road inaccessible | WX→HYD→TRF→EMS→HOS; HYD→PWR→COM; HOS↔EMS feedback | 1 (full depth) |
| **heat** | Heat-dome (3–6 days), humid variant | WBGT ≥ 32 °C for ≥ 3 h AND heat ED visits ≥ 2× baseline | WX→PWR (load)→outage→HLT/HOS; WX→HOS (lagged 12–48 h); PWR→COM | 2 |
| **grid** | Equipment fault / overload / storm-hit lines | ≥ X% customers out in zone ≥ 2 h | PWR→TRF (signals), PWR→COM, PWR→HOS (generator hours), PWR→HYD (pumps stop) | 3 |
| **epidemic** | Seeded outbreak, R0 sampled, mobility coupling | Projected ICU occupancy ≥ 90% | HLT→HOS (3–10 d lead), HOS→EMS diversion | 4 |
| **quake** | Mainshock + ETAS | MMI ≥ VII at populated zone OR damage index ≥ threshold | SEI→PWR, SEI→TRF, SEI→AIR (gas), SEI→HOS | 5 (lighter) |
| **chem** | Point release, random stability/wind | Concentration ≥ guideline level (AEGL/ERPG — **look the values up; do not hardcode from memory**) at populated zone | AIR→TRF (closure), AIR→HOS, AIR→EMS | 6 (lighter) |
| **compound-A** | Flood + grid + hospital strain interacting | any ≥ 3 layers critical in 12 h window | flood chain ⊗ grid chain, shared HOS/EMS bottleneck | demo finale |
| **compound-B** | Quake → chem leak + grid | same | SEI→{PWR, TRF, AIR}→HOS | demo finale |

Severity ladder per layer indicator: **0 normal · 1 stressed · 2 degraded · 3 failed**, thresholds in YAML. "Critical event" for a layer = level 3 sustained ≥ k hours.

### 4.4 Observation model (where adversity lives)
Every source has hidden params: noise σ, bias, drift, dropout rate, latency distribution (lognormal), duplication rate, out-of-order rate, reliability. Produce **`event_time`** and **`ingest_time`** separately; the system only sees `ingest_time ≤ as_of`.

Fault profiles (shipped as precomputed variants of every scenario):
- **F0** clean · **F1** dropout (20–40% random + one 6 h source blackout) · **F2** delay/out-of-order · **F3** bias/stuck-at on 5–10% sensors · **F4** adversarial (coordinated false citizen reports in a false zone + one coherently spoofed source) · **F5** all combined.

### 4.5 Scale
~700 anchor episodes (500 train / 100 val / 100 test) + 100 held-out-city episodes, split evenly across hazards, plus compound episodes. Vectorized NumPy: should generate in minutes on CPU. Seeds fixed and stored.

---

## 5. Data sources

Legend: ✅ confirmed to exist during research for this blueprint · ◐ recalled from memory — **search the exact slug on Kaggle before relying on it** · 🌐 not on Kaggle.

**Rule:** these datasets *calibrate simulator parameters and provide real replays*. They do not train the cascade model.

| Layer / hazard | Dataset | Use |
|---|---|---|
| Rain / flood (India) | ✅ *Rainfall in India 1901–2015* (monthly, by subdivision) | Seasonal rainfall regime, extreme-month frequency |
| Rain / flood | ✅ *Rainfall in Kerala 1901–2017* (ggopinathan) | Wet-regime tail calibration (2018 floods context) |
| Flood | ✅ *Flood Risk in India* (tabular: rainfall, infrastructure, history, flood flag) | Sanity check on rainfall→flood link; not time-series |
| Reservoir / hydro lag | ◐ *Chennai Water Management* (sudalairajkumar; daily reservoir levels + rainfall 2004–2019) | Rain→storage lag and recession constants |
| Sub-daily weather | ◐ *Historical Hourly Weather Data 2012–2017* (selfishgene; 36 cities hourly) | Diurnal profiles, hold-out city weather, heat regimes |
| Sub-daily weather | ◐ *Jena Climate* (10-min) | Short-lag meteorological dynamics |
| Delhi climate | ◐ *Daily Delhi Climate* | Heat regime marginals |
| Long-run temperature | ◐ *Berkeley Earth Global Land Temperatures* | Heat anomaly baselines |
| Traffic | ◐ *Metro Interstate Traffic Volume* (hourly + weather) | Demand profile, weather→speed sensitivity |
| Traffic | ◐ *Traffic Prediction Dataset* (fedesoriano; hourly junction counts) | Daily/weekly demand shape |
| Power demand | ◐ *Hourly Energy Consumption* (PJM) | Load diurnal/seasonal, temperature sensitivity |
| Power demand | ◐ *Individual household electric power consumption* (UCI) | Fine-grain load shape |
| Grid stability | ◐ *Smart Grid Stability* | Optional nonlinear stability feature check |
| Power outages | 🌐 **EAGLE-I** county outages 2014–2022, 15-min (ORNL / figshare; DOI 10.13139/ORNLNCCS/1975203 family) | Outage-duration and restoration-time distributions, storm-linked outage replay |
| Grid cascade benchmark | 🌐 PowerGraph (GNN benchmark on grid cascading failure, GitHub) | Optional external validation of grid stage structure |
| Emergency calls | ◐ *Emergency – 911 Calls* (mchirico; Montgomery Co. PA) | Call-rate diurnal shape, weather/incident sensitivity, burstiness |
| Citizen reports | ◐ *NYC 311 Service Requests* | Report burstiness, duplicates, flood/heat complaint statistics |
| Epidemic | ◐ *Novel Corona Virus 2019 Dataset* (SRK) and *COVID-19 in India* (sudalairajkumar) | Real Rt/epidemic-curve replay, reporting delay |
| Epidemic / hospital | ◐ OWID COVID-19 dataset mirror (hospital & ICU columns where present) | Case→admission→ICU lags |
| Air / gas sensors | ◐ *Air Quality Data in India 2015–2020* (rohanrao; city_day, station_hour) | Sensor noise, drift, spikes, missingness patterns for AIR layer |
| Earthquakes | ◐ *Significant Earthquakes, 1965–2016* (USGS) · 🌐 USGS ComCat via API | Real ETAS fit, real aftershock replay, live feed |
| Satellite flood (optional) | ◐ *Flood Area Segmentation* (small image set) | Optional only — skip unless ahead |
| Live feeds for demo | 🌐 Open-Meteo forecast API (no key) · 🌐 USGS GeoJSON earthquake feed | Live-adapter proof (Section 15) |

Chemical release: no Kaggle dataset I can vouch for. Use Gaussian-puff physics + AQ sensor noise from the India air-quality set. Say so.

Download everything into a Kaggle dataset you own (`/kaggle/input/...`) at H0 so notebooks are reproducible and offline.

---

## 6. Harness (build first — it is the temporal-validation answer)

### 6.1 Canonical event schema (Pydantic v2, versioned `v1`)

| Field | Type | Notes |
|---|---|---|
| `event_id` | str | Idempotency key; duplicates dropped |
| `source_id` | str | e.g. `gauge_017`, `scada_feeder_4`, `citizen_app` |
| `source_type` | enum | sensor · feed · citizen · forecast · official |
| `layer` | enum | WX HYD TRF PWR EMS HOS HLT AIR SEI COM |
| `zone_id` | str | H3 cell |
| `variable` | str | `rain_mm_h`, `bed_occ`, … |
| `value` | float | SI/standard units, documented in `variables.yaml` |
| `event_time` | ts (UTC) | When it happened |
| `ingest_time` | ts (UTC) | When the system could first know it |
| `issued_at` / `valid_for` | ts | Forecast products only |
| `quality` | float 0–1 | Source-declared, optional |
| `meta` | dict | Free-form (report text class, device id) |

Storage: Parquet partitioned by `scenario/fault_profile/date`. Query with DuckDB.

### 6.2 As-of discipline
- Single access point `store.view(as_of)` returns only rows with `ingest_time ≤ as_of`. Forecast products also require `issued_at ≤ as_of`.
- **Weather forecasts are covariates issued at `as_of`**, not the true future. Using the realized future as a "known covariate" is leakage — the most common way to fake good results.
- Labels are computed in a separate module that is never imported by inference code (enforce with an import-linter test).
- Scalers, thresholds, calibrators fit on train split only. Splits are by **episode and by city**, never random rows. For real replays use a 72 h embargo between train and test segments.
- Watermark: `watermark = as_of − max_allowed_lateness`; events later than that are logged as late, applied to state if still useful, never retro-edited into past forecasts.

### 6.3 Hash-chained ledger
Each forecast record: `{forecast_id, as_of, data_max_ingest_time, input_digest, model_version, outputs, prev_hash, hash}` with `hash = SHA256(prev_hash ‖ canonical_json(record))`.
- `data_max_ingest_time ≤ as_of` asserted at write.
- `GET /v1/ledger/verify` recomputes the chain and returns `{ok, n_records, first_bad}`.
- **Leakage canary test:** inject a fabricated spike at `t+6h` into a copy of the log; forecasts at `t` must be bit-identical. Show this in the demo.

### 6.4 Fault injector
Wraps the event stream (not the model): dropout, block outage, delay, reorder, duplication, bias, stuck-at, drift, spoof, coordinated false reports. Parameters in YAML; seed stored; each profile F0–F5 reproducible.

### 6.5 Replay clock
`as_of` advances by hourly ticks (forecast origin every 1 h in replay, Chronos refresh every 3 h to save compute). Time-warp factor, pause, seek, and scenario switch are control-plane calls (Section 15).

---

## 7. State estimation and adversity handling

### 7.1 Robust state per (zone, variable)
- Scalar Kalman-lite with **staleness-inflated variance**: `σ²(t) = σ²_last + q·(t − t_last)` — confidence decays when data stops.
- Multi-source fusion = reliability-weighted median, then Kalman update.
- Hampel filter (window 7, 3σ) on each raw stream; physical bounds from `variables.yaml` (reject rain > physical max, occupancy > 1.2 …).
- Cross-source consistency: neighboring-zone and cross-layer sanity (e.g., high power outage + normal traffic-signal sensors → flag).

### 7.2 Truth discovery (source reliability)
CRH-style EM on a rolling 24 h window:
1. For each (zone, variable, time-bucket) form claims from sources.
2. Consensus = reliability-weighted median.
3. Source loss = mean normalized |claim − consensus|; `r_s = exp(−λ·loss)` clipped to [0.05, 1].
4. Iterate 3–5 times; exponential forgetting `0.98/h`.
Output `GET /v1/sources/reliability` with trend sparkline.

### 7.3 Citizen reports
- Reporter trust ~ Beta(α, β): +1 α when corroborated by sensors or ≥2 independent reporters within 30 min/500 m; +1 β when contradicted by sensors.
- Report weight = trust × corroboration factor with diminishing returns (`1 − 0.5^n`).
- Cluster by (zone, 30 min). Burst detector: many new/low-trust accounts, same zone, no sensor corroboration → **quarantine**, show it on screen.
- Reports are **evidence for risk, never ground truth for labels**.

### 7.4 Graceful degradation (the number to show)
- `evidence_coverage_z = Σ(reliability × freshness) over sources / expected sum` per zone.
- Forecast intervals use **Mondrian conformal** with bins on `evidence_coverage` (e.g., ≥0.8, 0.5–0.8, <0.5): lower coverage → wider, still-valid intervals.
- State machine adds `confidence ∈ {HIGH, MED, LOW}`; at LOW the UI shows risk state with a hatched overlay, not a hidden one.
- Plot to show judges: **lead-time retention and ECE vs % corrupted/missing sources.**

---

## 8. Forecasting and calibrated risk

### 8.1 Per-layer forecasting with Chronos-2
- Targets: ~6 driver indicators per zone (rain, drain load/depth, traffic speed, load ratio, ED arrivals, temp/WBGT, concentration). Group related zones of the same indicator into one group so group attention cross-learns across zones (verified Chronos-2 mechanism).
- Known-future covariates: issued weather forecast (rain, temp, RH). Past-only covariates: other layers' states.
- Context 168 h, prediction length 72 h, quantiles (0.1, 0.5, 0.9). Use `Chronos2Pipeline.from_pretrained("amazon/chronos-2", device_map="cuda")` with `predict_df`/`predict` — **check the current README for the exact signature before coding**; do not trust memory.
- **Benchmark first (10 min):** measure series/s on your T4 at your context length. Set episode count from the measured number (budget in Section 16).
- Zero-shot is the default. LoRA fine-tune only if time remains **and** zero-shot CRPS on validation is clearly poor for a layer.
- For SEI and AIR layers Chronos adds little (event-driven); use ETAS and the puff model's own state instead. Do not force the foundation model where physics is better.
- CPU fallback for demo: `autogluon/chronos-2-small` (28M).

### 8.2 Features for the risk head (one hazard-agnostic model)
Per (zone, as-of):
- Current fused state of every indicator + trends (Δ1, Δ3, Δ6 h), EWMA, rolling max/min (6/24 h).
- Chronos-2 quantiles at +6, +24, +72 h for driver indicators; accumulated forecast rain/temperature excess over next 6/24/72 h.
- Neighbor aggregates: upstream (drainage graph), adjacent, feeder-sibling zones.
- Hawkes-derived: current intensity per type, expected downstream intensity, local branching ratio, active-loop flag.
- Early-warning signals (Scheffer et al. 2009): rolling variance and lag-1 autocorrelation of detrended indicators + 48 h Kendall-τ trend.
- Data quality: evidence coverage, mean staleness, mean source reliability.
- Static, **normalized relative to city** (elevation percentile, asset counts per capita, bed density) — absolute values will not transfer to a new city.
- "Trigger just detected" flags (quake detection, gas sensor spike) with age in hours.
- **Do not feed hazard type.** Hazard identity is inferred downstream from driver attribution. This is what lets it handle unseen scenarios.

### 8.3 Labels
For zone z, event type k, horizon h: `y = 1` if event k **onsets** in (t, t+h]. Event types: ≤7 per zone (access loss, power loss, hospital saturation, heat stress, contamination exposure, structural damage, comms loss) + city-level `cascade` (≥3 layers critical within 12 h and ≥2 coupled zones or ≥3 layers in one zone).
Censoring: events not occurring within the episode are 0 (censored at episode end) — keep a 72 h tail margin when building labels.

### 8.4 Training
- One LightGBM per event type. `horizon` is a feature with `monotone_constraints=+1`. Sample **one random horizon per row** (≈2–3 M rows total) rather than expanding all 7 — memory stays under ~2 GB.
- Params starting point: `num_leaves 63`, `lr 0.05`, `min_data_in_leaf 200`, `feature_fraction 0.7`, `bagging 0.8`, early stopping on validation **episodes**, `scale_pos_weight` only if you recalibrate afterward.
- Calibration: isotonic regression per event type on validation episodes. Check reliability diagram per horizon.
- Time-to-critical: invert the calibrated CDF at 0.1/0.5/0.9. If CDF(72 h) < 0.9, report "beyond 72 h, P(≤72h)=p". Never invent a median when mass is missing.
- Conformalization: CQR-style adjustment of the time-to-critical interval on validation, **Mondrian bins by evidence coverage**, ACI online update `α_{t+1} = α_t + γ(α − err_t)` (γ≈0.005) running on realized outcomes as they arrive.

### 8.5 Risk-state mapping (config, tuned on validation)

| State | Rule (zone) |
|---|---|
| CRITICAL | Any critical event active **or** P_any(≤12 h) ≥ τ_C |
| HIGH RISK | P_any(≤24 h) ≥ τ_H |
| WATCH | P_any(≤72 h) ≥ τ_W |
| NORMAL | otherwise |

Start with τ_W=0.20, τ_H=0.40, τ_C=0.60, then tune to a **false-alarm budget** (e.g., ≤1 false HIGH+ alert-episode per zone-week) using cost-loss reasoning (Murphy 1977; Richardson 2000). Hysteresis: upgrade immediately, downgrade only after 2 consecutive ticks below threshold. City-level state: CRITICAL if P_cascade(≤24 h) ≥ τ or ≥ m zones CRITICAL; HIGH if P_cascade(≤48 h) ≥ τ' or weighted-exposure rule; etc. Weight by population/asset exposure.

---

## 9. Dependency discovery and cascade engine

### 9.1 Event extraction
Upward crossings of severity ≥2 ("degraded") and =3 ("failed") per layer per zone → 20 event types. Bin hourly → count tensor `N[t, zone, type]`.

### 9.2 Discrete-time multivariate Hawkes (point-process GLM)
```
λ_{z,i}(t) = μ_i  +  Σ_j Σ_b  A[i,j,b] · C_b[j](z,t)      (all terms ≥ 0, so λ ≥ 0)
where C_b[j](z,t) = lag-basis-b convolved counts of type j in zone z
                    + s_j · Σ_{z'∈adj(z)} W_{zz'} · (same for z')
basis b ∈ {τ=2 h, 8 h, 24 h} exponential decays; s_j = spatial spillover per source type
```
- Loss: Poisson NLL + L1 on `A` + group-lasso per edge; `A ≥ 0` via softplus/clamp.
- Mask: forbid physically impossible edges (e.g., anything → WX; HOS → SEI). Masks **forbid**, never assert. Disclose this.
- Params ≈ 20×20×3 + 20 + 20 ≈ 1.2 k. Fits in minutes on CPU, seconds on GPU.
- **Branching ratio ρ** = spectral radius of integrated kernel `Σ_b A[:,:,b]·τ_b` (extend with spatial operator for the full zone-type matrix). ρ ≥ 1 ⇒ supercritical, cascade can self-sustain. Headline metric: **"cascade reproduction number."**
- **Edge sensitivity:** `∂ρ/∂A_ij = u_i v_j / (uᵀv)` (left/right eigenvectors) → ranks which edges/nodes most amplify the cascade, almost free.
- **Loops:** strongly connected components with loop gain > 1 (e.g., HOS→EMS→HOS). Output loop list and gain.

### 9.3 Online update
- Warm start from a pooled prior fit across training episodes (hierarchical shrinkage: `A_city = A_prior + δ`, L2 on δ).
- Every hour: 5 Adam steps on the last 7 days with exponential sample weights (half-life ≈ 48–72 h; tune on drift scenario).
- Change-point on each edge's weight (CUSUM on normalized change). Raise "dependency changed" event: e.g., drainage pump failure strengthens HYD→TRF.
- Demo beat: change a coupling mid-run (blocked drain) → graph edge visibly strengthens within hours.

### 9.4 Edge evidence cards (what makes the graph credible)
For each edge i←j: weight, lag peak, block-bootstrap/Fisher CI, likelihood-ratio test vs refit without edge, count of "j preceded i within lag" instances vs shuffled-timing baseline, mechanism tag (physical / cyber / geographic / logical — Rinaldi et al. 2001 taxonomy) from a small prior table, and an **unsupported-correlation flag** if statistically present but with no plausible mechanism.

### 9.5 Chain and timing inference
1. Condition on current event history; forward-simulate fitted Hawkes (thinning, 300–500 paths, 72 h) on CPU/GPU.
2. Per path record first-occurrence times for each type.
3. Outputs: **stage ETA distribution** per type (median, 10–90%), **top-3 chains** by frequency of ordering among paths reaching critical, branch probabilities, chain probability.
4. Reconcile with the GBM: marginal CDFs come from the calibrated GBM; MC supplies ordering and joint structure. If MC marginal and GBM marginal differ by > threshold, mark chain `LOW CONFIDENCE` and widen intervals. Enforce ETA ordering along chain; if violated, flag.
- **Simultaneous / interacting cascades:** compute `interaction_gain = P(joint critical) / (P(A)·P(B))` from MC with shared bottleneck nodes (HOS, EMS). >1 means compounding; show it.

### 9.6 ETAS (seismic)
Fit `λ(t,m) = μ + Σ_i K·10^{α(m_i−m_0)}(t−t_i+c)^{−p}` by MLE on the real USGS catalog; sample aftershock sequences for the SEI layer; output aftershock probability by magnitude over 1–72 h. It is Hawkes, so its parents/kernels display in the same UI.

---

## 10. Interventions and counterfactuals

### 10.1 Intervention catalog (YAML, assumptions explicit)

| Hazard | Intervention | Effect model | Cost / resource | Deploy lead | Side-effect |
|---|---|---|---|---|---|
| Flood | Pre-position pumps in zone | HYD→TRF edge ×(1−e), drain cap ↑ | pumps, crew | 3–6 h | crew diverted from other zones |
| Flood | Pre-emptive road closure + reroute | TRF load shift | police units | 1 h | congestion in adjacent zones |
| Flood | Evacuate low-lying zone | Reduces HOS/EMS demand later | buses, shelters | 6–12 h | **TRF congestion ↑**, shelter load |
| Flood/Grid | Backup generator to hospital/substation | PWR→HOS edge ×(1−e) | generators, fuel | 2–4 h | fuel draw |
| Heat | Open cooling centers | Reduces heat ED visits | venues, staff | 6–12 h | PWR load ↑ |
| Heat | Rolling load-shed / demand response | PWR overload ↓ | none | 0–1 h | HLT exposure ↑ in shed zone |
| Epidemic | Surge beds / divert | HOS capacity ↑ | staff, equipment | 12–48 h | EMS travel ↑ |
| Quake | Close damaged routes / stage ambulances | TRF/EMS | units | 1–3 h | access loss |
| Quake | Gas isolation valve closure | SEI→AIR edge ↓ | crews | 1 h | service loss |
| Chem | Shelter-in-place vs evacuate zone | Exposure ↓ | alerts, buses | 0.5–2 h | TRF ↑ if evacuate |
| Any | Pre-alert hospitals / stage ambulances | HOS/EMS buffer | units | 1–3 h | — |

Effect sizes are **assumptions with ranges**, labeled as such. Show sensitivity bands in the demo.

### 10.2 Counterfactual computation
- Paired simulation with **common random numbers**: draw uniform noise stream once; run baseline and intervened model with the same stream so the difference isolates the intervention (lightweight practical approximation of counterfactual simulation; the Gumbel-Max counterfactual TPP from Noorbakhsh & Rodriguez, NeurIPS 2022, is the rigorous version — cite it as the direction, do not claim it).
- Intervention operators: scale selected edges, shift μ, add side-effect edges, cap capacities.
- Outputs per intervention: ΔP(critical ≤ h), Δ stage ETAs, Δρ, side-effect impact, cost, resource use.
- **Deadline clock:** scan start offsets 0…Δ h; "latest start such that ΔP(critical) retains ≥ 80% of its maximum." Display as countdown per intervention.

### 10.3 Allocation under limits
Maximize Σ_z w_z · ΔP_z subject to resource pools (pumps, crews, ambulances, generators, shelter seats) with time-to-deploy and side-effect penalties. Use `scipy.optimize.milp` on pre-computed single-intervention gains plus pairwise interaction corrections from re-simulation of the top-k combos (lazy greedy fallback). Return plan, unallocated risk, and next-best option.

### 10.4 Ground-truth verification (rare strength)
Apply the recommended plan **inside the true simulator** and compare realized vs predicted risk reduction. Report calibration of the counterfactual (predicted ΔP vs realized ΔP scatter). If this is bad, say so and shrink claimed effects.

---

## 11. Explainability

| Question | Method | Output |
|---|---|---|
| Why did zone risk change in the last tick? | TreeSHAP on GBM, grouped into layer-level drivers; Δ since previous tick | Top-5 driver bars with signed contribution |
| Which upstream failure is pushing this node? | Exact Hawkes parent attribution: share of `λ_i` from each (j, lag-basis) | Parent ranking per node |
| What is the predicted chain and why each link? | Edge evidence cards (Section 9.4) | Chain with evidence per arrow |
| Is this a data problem? | Source reliability + evidence coverage | Confidence badge + culprit sources |
| What would change the outcome? | Counterfactual (Section 10) | Ranked actions |

Narrative text is **template-generated** from structured JSON. Optional LLM rewrite only if its output passes a regex check that every number and entity appears in the input JSON; otherwise fall back to the template. LLMs never produce probabilities, states, or ETAs.

---

## 12. Online learning and drift

| Component | Update rule | Trigger |
|---|---|---|
| Hawkes weights | Adam steps, sliding window, exponential forgetting | hourly |
| Online residual corrector | River linear model on GBM log-odds residuals | per outcome as realized |
| Calibration | Windowed isotonic refresh + ACI α update | per outcome |
| Source reliability | EM with forgetting | hourly |
| Reporter trust | Beta updates | per report |
| Drift detection | ADWIN on prediction error and on feature means; Page-Hinkley on edge weights | continuous |
| GBM structure | **Not** retrained online. Retrain offline only if drift alarms persist — say this plainly | manual |

Drift scenario for demo: shift rainfall–drainage response mid-episode (e.g., new construction lowers drain capacity). Show ADWIN alarm, edge change, corrector adapting, calibration recovering.

**Cold start on an unseen city:** use the pooled prior; Chronos-2 zero-shot; relative-normalized statics; Hawkes adapts online. Plot performance vs hours of data seen in the new city (the "cold-start curve").

---

## 13. Evaluation protocol (what the scoreboard shows)

All numbers from **rolling-origin replay through the harness**, never from random row splits. Report on: anchor-test episodes, **held-out city**, each fault profile, each hazard.

### 13.1 Metrics

| Claim | Metric | How |
|---|---|---|
| Lead time | Median/IQR lead (event onset − first HIGH+ alert) **at a fixed false-alarm budget** | Alert-episode merging (gap ≥ 6 h = new episode); false alarm = alert episode with no critical onset within its horizon |
| False alarms | False alert-episodes per zone-week; precision at budget | Same alert logic |
| Calibration | Reliability diagram per horizon, ECE, Brier + decomposition | Pooled over test episodes |
| Time-to-critical | Median abs error, interval coverage (nominal 80/90%), interval width | Conformalized intervals; coverage must be within ±3 pts |
| Stage timing | Per-stage ETA error vs true stage onset | Compare against simulator truth |
| Dependency discovery | Edge AUROC/F1 vs `G_true`, lag error (h), time-to-detect a changed edge | Baseline: lagged correlation |
| Cascade ordering | Kendall-τ of predicted vs true stage order; top-1/top-3 chain hit rate | |
| Online learning | Error recovery time after injected drift; ADWIN detection delay | With vs without online updates |
| Adversity | Lead-time retention, ECE, coverage vs % sources corrupted (0–50%) | F1–F5 sweep |
| Generalization | Same metrics on held-out city; cold-start curve | Never tuned on it |
| Counterfactual | Predicted vs realized ΔP in ground-truth simulator | Scatter + slope |
| Temporal isolation | Ledger verify + leakage canary pass | Binary |

### 13.2 Baselines (must be on the scoreboard)
Persistence/threshold rules · climatology · GBM without cascade/Hawkes features · Chronos-2 alone with thresholding · lagged-correlation graph. A system without baselines is an anecdote.

### 13.3 Ablations (one slide)
No Hawkes features · no truth discovery · no Mondrian bins · no online updates · no Chronos covariates · no spatial spillover.

### 13.4 Target thresholds (internal goals, not promises — report what you get)
Median lead ≥ 24 h flood/heat; ≥ 6–12 h grid; ECE ≤ 0.05; 80% interval coverage within 77–83%; edge F1 ≥ 0.7 anchor; held-out-city drop ≤ 25% relative; lead-time retention ≥ 70% at 30% source dropout.

---

## 14. Output catalog (everything the system can produce)

**A. Risk and timing**
1. Four-state risk per zone, per layer, and city-wide, with hysteresis
2. Calibrated P(critical ≤ h) for h ∈ {1,3,6,12,24,48,72}, per zone × event type
3. Time-to-critical median and 80/90% intervals (or "beyond 72 h, P=…")
4. Per-stage ETA with uncertainty for every stage in the chain
5. Confidence badge (HIGH/MED/LOW) with reason
6. Expected population exposed and critical assets at risk (hospitals, substations) per zone
7. City-level cascade probability and **cascade reproduction number ρ**
8. Early-warning signals: rolling variance, autocorrelation, Kendall-τ per layer

**B. Cascade**
9. Most probable failure chain + top-3 alternatives with probabilities
10. Branching points and branch probabilities
11. Feedback loops with loop gain (e.g., HOS↔EMS)
12. Compound-cascade interaction gain (joint vs independent)
13. Zone-to-zone spread forecast (flood path, plume footprint, outage spread, epidemic mobility)
14. Hazard attribution (what the system thinks is driving risk), no hazard label given

**C. Dependency discovery**
15. Weighted, lagged, directed layer graph (zone-pooled and per-zone)
16. Edge evidence cards, CIs, unsupported-correlation flags
17. Graph time series; change-point alerts ("dependency changed")
18. Most amplifying nodes/edges (∂ρ/∂A ranking)
19. Recovered-vs-true graph score (simulator mode)

**D. Hazard-specific**
20. Flood: waterlogging depth forecast map, road-accessibility loss, drain-overload ETA
21. Heat: WBGT forecast, heat-ED surge ETA, cooling-center demand, grid load vs rating
22. Epidemic: Rt, doubling time, ED→hospital→ICU surge forecast, peak ETA, capacity breach ETA
23. Grid: customers-out forecast, substation overload ETA, hospital generator-hours remaining, restoration forecast
24. Quake: aftershock probability by magnitude and hour (ETAS), expected shaking by zone, damage index, shelter demand, gas-leak trigger risk
25. Chem: plume footprint over next hours, shelter-in-place vs evacuate zones, downwind population, hospital casualty forecast
26. Hospital: bed/ICU/ED-boarding forecast, diversion risk, supply-days remaining
27. EMS: response-time map, coverage gaps, unit-shortfall forecast

**E. Decisions**
28. Ranked interventions with cost, resource use, expected ΔP(critical), Δ stage ETAs, Δρ
29. Side-effect report per intervention (congestion, load, crew diversion)
30. Deadline clocks ("act by T")
31. Resource-constrained allocation plan, unallocated risk, next-best alternative
32. What-if sliders (resources, intervention start time) with live counterfactual curves
33. Sensitivity bands on assumed intervention effects
34. Predicted-vs-realized counterfactual check (simulator mode)

**F. Evidence and trust**
35. Per-risk-change driver decomposition (SHAP groups + Hawkes parents)
36. Source reliability table + trends; quarantined sources/report clusters
37. Evidence coverage per zone; data staleness map
38. Data-fault log (dropouts, delays, spoof detections)
39. Drift alarms and online-learning status
40. Hash-chained forecast ledger + verify result + leakage-canary result

**G. Evaluation**
41. Lead-time-vs-false-alarm curve, reliability diagrams, coverage plot
42. Fault-sweep degradation curves
43. Held-out-city report and cold-start curve
44. Baseline and ablation tables
45. Auto-generated model card and limitations page

**H. Integration artifacts**
46. **CAP v1.2 XML** alerts (standard emergency-alert format) per zone/state change
47. GeoJSON risk layers (zone state, plume, flood extent proxy)
48. Prometheus `/metrics` and `/healthz`
49. Adapter registry showing which sources are replay vs live
50. OpenAPI spec (auto from FastAPI) and a one-page integration guide
51. Plain-language bulletin per zone (template; optional LLM paraphrase with numeric guard)
52. CSV/Parquet export of any scenario run

---

## 15. Demo mode (most important section)

### 15.1 Design principle
**Deterministic, offline, instant, and honest.** The demo must not depend on internet, GPU, or luck.

- **Replay mode (default):** each scenario × fault profile is produced **offline through the real pipeline** (same code as production path) and stored as a run directory (Parquet ledger + outputs). The demo server streams it with time-warp. Switching faults = switching precomputed runs, instantly.
- **Live-recompute toggle ("Run last 6 h live"):** recomputes the last N hours on CPU with `chronos-2-small`, same ingest API; numbers should match cached within tolerance. This answers "is it really running?"
- **Live-adapter mode (proof of production path):** real feeds through the identical `/v1/ingest` contract — Open-Meteo forecast (rain/temp) and USGS earthquake GeoJSON feed for a real city — with automatic fallback to a cached snapshot if offline. State it clearly: only the sources with public APIs are live; the rest are replay.
- Interactive pieces that are **truly live**: what-if interventions, graph evidence drill-down, ledger verify, leakage canary, quarantine view, state-vs-time seek.

### 15.2 Control plane (demo-only endpoints)

| Endpoint | Purpose |
|---|---|
| `POST /demo/scenario {id, city, fault_profile}` | Load run |
| `POST /demo/speed {x}` | Time-warp (1 sim-hour ≈ 0.5–2 s) |
| `POST /demo/seek {as_of}` / `/demo/pause` / `/demo/play` | Transport |
| `POST /demo/fault {profile}` | Swap F0–F5 variant at current as_of |
| `POST /demo/drift {kind}` | Load drift variant |
| `GET /demo/scenarios` | Catalog with one-line description and lead semantics |

### 15.3 Production API (the proof that this runs on real data)

| Endpoint | Description |
|---|---|
| `POST /v1/ingest` | Batch of canonical events; returns `{accepted, duplicates, rejected[], watermark}`; idempotent on `event_id`; schema-validated; late-arrival policy |
| `GET /v1/risk?as_of=&zone=` | States, P(h), T_crit quantiles, confidence |
| `GET /v1/cascade?zone=\|city` | Chains, stage ETAs, branches, ρ, loops |
| `GET /v1/graph` · `/v1/graph/history` · `/v1/graph/edge/{i}/{j}` | Dependency graph + evidence |
| `GET /v1/explain?zone=&layer=&as_of=` | Drivers and parents |
| `POST /v1/intervene` | What-if (interventions, start offsets, resources) |
| `GET /v1/recommend` | Allocation plan |
| `GET /v1/sources/reliability` | Reliability, quarantines |
| `GET /v1/ledger/verify` · `/v1/ledger/{id}` | Audit |
| `GET /v1/metrics/eval` | Scoreboard JSON |
| `GET /v1/alerts.cap` · `/v1/risk.geojson` | Integration outputs |
| `GET /v1/adapters` | Source registry: replay vs live, last-seen, lag |
| `WS /v1/stream` | State/alert push |
| `GET /healthz` · `/metrics` | Ops |

**The replayer is just a client of `/v1/ingest`.** Show that in the architecture slide: replay → HTTP → same endpoint production adapters would call.

Production-mapping slide (mapping only, nothing integrated): rainfall/river gauges ← IMD/CWC-type feeds; outages ← DISCOM/SCADA; hospital beds ← hospital management systems; ambulance/emergency calls ← 108/112 dispatch feeds; traffic ← commercial traffic APIs; satellite ← Sentinel/IMERG; seismic ← NCS/USGS; air/gas ← CPCB-type monitors; citizen reports ← app/helpline. Mark clearly as "adapter contract defined, not integrated."

### 15.4 UI screens (single page, tabs or panels)
1. **Command map:** zone polygons colored by state, city badge, T-minus clock to critical, layer toggles, hatched overlay for LOW confidence. Basemap tiles only when online; default blank background so it never breaks offline.
2. **Cascade timeline:** Gantt of predicted stages with uncertainty bars, realized stages overlaid as they happen, top-3 chains switcher.
3. **Dependency graph (Cytoscape):** weighted lagged edges; click → evidence card; time slider shows graph evolution; changed-edge highlight.
4. **Why panel:** driver bars + parent ranking + data-health badge.
5. **Intervention lab:** resource sliders, start-time slider, counterfactual curves vs baseline, side-effect list, deadline clocks, allocation plan.
6. **Data health:** source reliability, delay/dropout, quarantined clusters, fault-profile switcher, evidence coverage map.
7. **Scoreboard:** lead-time vs FAR, reliability, coverage, held-out city, fault sweep, ablations, ledger verify, leakage canary.
8. **Scenario drawer:** hazard picker, city picker, speed control.

Build the UI by giving an AI coding assistant the OpenAPI JSON and this screen list. Contract first; the UI is a thin client. Mock the API with JSON fixtures at H8 so UI and backend proceed in parallel.

### 15.5 Demo script (≈10–11 min)

| Time | Beat | What judges see |
|---|---|---|
| 0:00 | Thesis (20 s) | "We forecast the cascade, not the event. Same pipeline, six hazards." |
| 0:20 | **Flood (2:30)** | NORMAL → WATCH at T−68 h as rain forecast arrives; chain forms on timeline; time-to-critical clock; click an edge → evidence card; flip to F5 faults → confidence drops, intervals widen, lead mostly retained; quarantine of fake reports; intervention lab → counterfactual curves + deadline clock; ledger verify + leakage canary |
| 3:00 | Heatwave (1:00) | Load/outage/hospital chain; rolling load-shed side effect shown |
| 4:00 | Grid failure (1:00) | Fault-triggered cascade; branching ρ crossing 1 |
| 5:00 | Epidemic (1:00) | Syndromic lead into hospital capacity breach ETA; Rt |
| 6:00 | Earthquake (1:00) | Say "clock starts at detection"; ETAS aftershock curve; secondary cascade |
| 7:00 | Chem leak (1:00) | Plume footprint, shelter vs evacuate with congestion side-effect |
| 8:00 | Compound-A (1:30) | Two cascades interact; interaction gain >1; shared hospital bottleneck |
| 9:30 | Held-out city (0:30) | Same engine, unseen city; cold-start curve |
| 10:00 | Scoreboard + production proof (0:45) | Calibration, lead vs FAR, baselines; `/v1/ingest`, live Open-Meteo/USGS adapters, CAP alert |

Also prepare the 3 sentences on honesty: (1) simulator-based validation with real-calibrated parameters and real replays where data exist; (2) no precursor claim for quake/chem; (3) intervention effects are stated assumptions with sensitivity bands.

### 15.6 Failure drills (do before the demo)
- Run on a CPU-only laptop with Wi-Fi off. Everything except live adapters must work.
- Pre-warm: load all runs into memory at startup; first click must be instant.
- `make demo` starts everything; second terminal not required.
- Pin dependencies; build a Docker image **and** keep a venv fallback.
- Record a full-run backup video at H23.
- Fixed seeds, fixed scenario IDs, screenshots of every screen for the slide deck.
- Rehearse with a stopwatch twice; cut anything that overruns.

### 15.7 Hard questions to rehearse
| Question | Answer |
|---|---|
| "Is this trained on real cascades?" | No such labeled data exists publicly. Calibrated simulator + real replays; ground truth lets us score dependency recovery and counterfactuals. |
| "Doesn't the model just learn your simulator?" | Simulator uses different mechanics (queues, SCS-CN, SEIR, puffs) from the model (Hawkes/GBM); held-out city has different parameters; real replays for quake/epidemic/outage statistics. |
| "How do you avoid future leakage?" | `as_of` store, issued-forecast covariates, hash-chained ledger, canary test. |
| "Online learning?" | Hawkes SGD, River corrector, ACI, reliability EM, ADWIN; GBM is intentionally not retrained online. |
| "What if sensors lie?" | Truth discovery, quarantine, Mondrian conformal; show F4/F5 curves. |
| "Counterfactuals are assumptions" | Yes: effect sizes are catalog assumptions with sensitivity bands; verified against simulator truth. |
| "Quake/chem can't be predicted" | Correct, and we say so; we forecast the cascade after detection. |

---

## 16. Compute and time budget

### 16.1 Kaggle T4 budget (hard cap 10 h)

| Job | GPU h (cap) | Notes |
|---|---|---|
| Chronos-2 benchmark + smoke test | 0.3 | Measure series/s; set episode count from it |
| Chronos-2 feature extraction (train/val/test/held-out) | ≤3.0 | 900 episodes × 40 refreshes (every 3 h) × ~30 series ≈ 1.1 M forecasts; at an *assumed* 100–150 series/s ≈ 2–3 h. **If measured < 100/s, drop to 600 episodes** |
| Hawkes pooled prior + per-hazard fits | 0.5 | Can run on CPU |
| Chronos-2 LoRA fine-tune (optional) | ≤1.5 | First thing cut |
| Full eval replay (F0 and F5 on all test+held-out; other profiles on 30-episode subset) | 1.5 | Chronos refresh every 3 h |
| Demo-run precompute (8 scenarios × 6 profiles) | 0.5 | |
| Counterfactual verification runs | 0.5 | Mostly CPU |
| Reserve for reruns/crashes | ≥1.5 | Never plan to 100% |
| **Total planned** | **≤9.8 h** | LightGBM, ETAS, truth discovery, MILP run on CPU in parallel |

Train/serve parity: GBM training features must use the **same Chronos staleness** as serving (forecast from the latest 3 h refresh), or calibration will break at demo time.

Kaggle practicalities (verify against your account): run long jobs as **committed versions** (survive tab closes), checkpoint every stage to `/kaggle/working` and publish as a Kaggle dataset, write logs to Parquet, keep each stage resumable. Hyperparameter sweeps are the real quota killer — use ≤10-config grids with fixed seeds.

### 16.2 24-hour plan

| Hours | Work | Exit gate |
|---|---|---|
| 0–1 | Repo, schemas, `variables.yaml`, plugin YAMLs, datasets into one Kaggle dataset, pick anchor/held-out cities | Schemas frozen |
| 1–7 | Simulator core + flood, heat, grid, epidemic plugins; calibrate marginals from data | Plots look physically sane; `G_true` saved |
| 7–8 | Quake + chem plugins (light); generate all episodes; Chronos benchmark | Episodes on disk; series/s known |
| 8 | **Launch Chronos extraction on Kaggle (background)** | Job running |
| 8–14 | Harness, ledger, fault injector, state estimator, truth discovery, event extractor, Hawkes, FastAPI skeleton, UI shell on mocks | Replay through `/v1/ingest` works; leakage canary passes |
| 14–17 | GBM training, calibration, conformal + ACI + Mondrian, state mapping, eval v1 | **Kill gate** (below) |
| 17–20 | MC cascade, counterfactuals, MILP, explain; precompute all demo runs; held-out-city eval (single pass) | All endpoints return real data |
| 20–23 | UI polish, scoreboard, demo script, failure drills, model card | Two clean rehearsals |
| 23–24 | Freeze, backup video, buffer | No new features |

**Kill gates**
- H14: flood event labels exist and a trivial baseline works; if not, event definitions are wrong — fix before modeling.
- H17: Hawkes edge F1 vs `G_true` ≥ 0.5 and beats shuffled-timing baseline on held-out episodes; if not, fix event extraction/lag basis before adding anything.
- H17: GBM beats persistence/threshold baseline on validation lead time at fixed FAR; if not, features or labels are broken.
- H20: any hazard plugin without a working chain → ship it as "simulated demo with fewer instrumented layers" rather than hiding it.

**Cut order if behind:** LoRA → compound-B → live-recompute toggle → LLM bulletin → MILP (use lazy greedy) → ETAS depth → chem depth.
**Never cut:** harness + ledger + canary, fault injection, calibration plots, held-out city, dependency graph with evidence, counterfactual panel, CAP/ingest endpoints.

---

## 17. Repository layout and dependencies

```
warning72/
  configs/        variables.yaml  cities/*.yaml  plugins/{flood,heat,grid,epidemic,quake,chem}.yaml
                  interventions.yaml  thresholds.yaml  faults.yaml
  sim/            core.py  layers/*.py  plugins/*.py  observe.py  gen_episodes.py
  harness/        schema.py  store.py (as-of)  ledger.py  faults.py  replay.py
  state/          estimator.py  truth_discovery.py  citizen_trust.py
  forecast/       chronos_runner.py  features.py  labels.py(not imported by inference)
  cascade/        events.py  hawkes.py  etas.py  mc.py  evidence.py  loops.py
  risk/           gbm.py  calibrate.py  conformal.py  states.py
  decide/         interventions.py  counterfactual.py  allocate.py  deadline.py
  explain/        shap_groups.py  parents.py  narrative.py
  online/         drift.py  corrector.py
  eval/           metrics.py  baselines.py  ablations.py  report.py
  api/            main.py  routes/*.py  cap.py  geojson.py  demo_control.py
  ui/             index.html  app.js  (MapLibre, ECharts, Cytoscape via CDN, vendored copies for offline)
  runs/           <scenario>/<fault>/{ledger.parquet,outputs.parquet}
  tests/          test_asof.py  test_canary.py  test_ledger.py  test_schema.py  test_import_boundary.py
  Makefile  Dockerfile  README.md  MODEL_CARD.md
```

Dependencies (pin exact versions at H0): Python 3.11 · torch 2.x · `chronos-forecasting>=2.0` · lightgbm · scikit-learn · shap · river · polars · duckdb · pyarrow · numpy · scipy · statsmodels · networkx · h3 · fastapi · uvicorn · pydantic v2 · orjson · pytest. Optional: pandapower, tigramite. **Vendor all JS libraries locally** (CDN is not reliable at a venue).

---

## 18. Do and Don't

### Do
1. Build the harness, ledger, and canary test first. Everything else is only credible on top of it.
2. Keep one hazard-agnostic risk model; hazard identity is derived, not given.
3. Use issued weather forecasts (with realistic error growth) as covariates — never realized weather.
4. Split by episode and city; lock the held-out city and touch it once.
5. Keep simulator mechanics different from model mechanics.
6. Save `G_true` per episode; score dependency discovery against it.
7. Calibrate on validation **episodes**, check reliability per horizon, enforce monotone CDFs.
8. Report lead time at a **fixed false-alarm budget**, not accuracy.
9. Show degraded confidence visibly (hatching, wider intervals) rather than hiding zones.
10. Use hysteresis on states; flapping destroys trust.
11. Put every assumption in YAML (thresholds, intervention effects, masks) and print them on a limitations page.
12. Keep train/serve parity for Chronos staleness and feature definitions.
13. Define critical events precisely and in config; cite guideline sources for chem thresholds (look them up).
14. Checkpoint every stage; make each resumable; log to Parquet.
15. Mock the API early so UI and backend proceed in parallel.
16. Precompute all demo runs; test offline on the demo machine.
17. Vendor JS assets; default to a blank basemap.
18. State lead-time semantics per hazard before a judge asks.
19. Include baselines and ablations on the scoreboard.
20. Rehearse the failure drills and keep a backup video.

### Don't
1. Don't pass realized future weather/state to any forecaster, even "just for the demo."
2. Don't shuffle rows or use random k-fold on time series.
3. Don't let an LLM emit probabilities, states, or ETAs.
4. Don't claim to predict earthquake or chemical-release onset.
5. Don't present simulated results as real-world accuracy.
6. Don't tune anything on the held-out city.
7. Don't hardcode per-city absolute statics into the model; use relative/normalized values.
8. Don't run hyperparameter sweeps on GPU quota.
9. Don't add Kafka, Spark, RL, Kubernetes, MLflow, or a new framework mid-build.
10. Don't retrain the GBM online and claim "online learning" — be precise about which parts adapt.
11. Don't treat citizen reports as labels.
12. Don't hide failed kill-gates; adjust scope and say so.
13. Don't use Streamlit for the streaming map; it will lag and rerun.
14. Don't depend on internet, GPU, or a cloud service during the live demo.
15. Don't give hazard plugins bespoke architectures; they share one engine.
16. Don't let the graph show edges without evidence cards.
17. Don't use Gumbel-Max/neural-TPP counterfactual claims; say "paired simulation with common random numbers."
18. Don't build a satellite pipeline unless everything else is done.
19. Don't leave statistics for the scoreboard until the last hour; evaluation code runs from H14.
20. Don't add features judges cannot see or call.

---

## 19. Risks and fallbacks

| Risk | Mitigation / fallback |
|---|---|
| Weak real data for chem, hospital, EMS | Physics + calibrated marginals; label as simulated; real replays only where they exist |
| Inverse-crime accusation | Different mechanics for sim vs model; held-out city; real replays |
| Chronos throughput lower than assumed | Benchmark at H7; reduce episodes; use `chronos-2-small`; refresh every 6 h in training with matched serving |
| Hawkes fails to recover edges | Check event thresholds and lag basis first; ablate spatial term; stronger L1; cross-check with PCMCI+ offline |
| GBM miscalibrated across horizons | Isotonic per horizon; monotone constraint; Mondrian bins; ACI online |
| Kaggle session loss | Committed runs, per-stage checkpoints, Parquet logs |
| UI time sink | Contract-first thin client, vendored libs, AI-generated scaffold, cut screens in this order: scenario drawer polish → data-health extras → graph history |
| Compound cascade looks scripted | Show interaction gain from MC and let the judge change resource sliders live |
| Demo machine surprise | Offline-first, `make demo`, Docker + venv, backup video |
| Counterfactual effect sizes challenged | Sensitivity bands, simulator-truth verification, explicit assumption tags |

---

## 20. Final checklist (freeze at H23)

- [ ] Leakage canary and ledger verify green on every shipped run
- [ ] Reliability diagrams and coverage within tolerance on anchor-test **and** held-out city
- [ ] Lead-time-vs-FAR curve with baselines on the scoreboard
- [ ] Fault sweep F0–F5 plotted; graceful degradation visible
- [ ] Dependency graph with evidence cards; recovered-vs-true score shown
- [ ] Drift scenario shows alarm → edge change → recovery
- [ ] All six hazards + Compound-A run end-to-end from the control plane
- [ ] Intervention lab: counterfactual, side-effects, deadline clock, allocation
- [ ] `/v1/ingest`, `/v1/adapters`, CAP, GeoJSON, `/healthz`, `/metrics` respond
- [ ] Live Open-Meteo/USGS adapters work with cached fallback
- [ ] Limitations page + model card written
- [ ] Offline run on a CPU laptop passes; backup video recorded
- [ ] Two timed rehearsals complete in ≤ 11 minutes
