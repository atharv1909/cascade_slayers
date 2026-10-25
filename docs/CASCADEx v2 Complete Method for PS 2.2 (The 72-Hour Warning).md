# CASCADEx v2: Complete Method for PS 2.2 (The 72-Hour Warning)

*Refines your Research & Build Blueprint and Source Manifest, and adds a Cities: Skylines-style interface. 25 October 2026.*

## 0. Read this first

- **Nothing came through under “(pasted)”.** This doc is built from your blueprint, your source manifest and your Skylines idea. Send the pasted ideas and I will merge them in.
- **The event is today.** The blueprint’s first-hour data gate (MCGM query, rainfall zip, AOI choice) is the first thing to do. Nobody has verified the MCGM layers actually download; the blueprint says so itself.
- **“glm” in your message:** I read it as GL, meaning MapLibre GL / WebGL, since that is what renders the 3D city. If you meant the GLM language model, the blueprint rule still holds: no external LLM, because the venue is offline and a model can invent causal stories. A local template can narrate each receipt instead.

### What this version changes from the blueprint

1. **Ensemble forcing and Monte Carlo.** Instead of one deterministic run, run the cascade across weather-ensemble members and uncertain parameters. That yields time-to-critical *distributions* and “share of scenarios where X happens”.
2. **Real online learning.** The blueprint says no labels exist for online learning. Wrong for rainfall: station observations are the labels for forecast rainfall. Online bias-correct the forecast against them.
3. **Rainfall rarity instead of arbitrary scaling.** Normalize rainfall by the station-history percentile and anchor the alert thresholds to IMD rainfall classes.
4. **A dependency-discovery module** that runs on simulated streams, controls for the rain confounder, and keeps learned-only edges as hypotheses. The blueprint dodged this PS requirement.
5. **A feedback loop and two labelled optional branches** (evacuation congestion, power substations). Without them the PS’s “branching, feedback loops” item is thin.
6. **Robust interventions.** Optimize the expected outcome and the worst decile, compare against naive placements, and report whether the ranking is stable under assumption changes.
7. **Fix circular validation.** The blueprint uses flood-spot proximity as a feature and then validates against flood spots. Hold some hotspots out.
8. **Hysteresis** on risk states, to avoid the alert flip-flopping the PS warns about.
9. **Demo-scenario reality check.** A live Mumbai forecast taken in late October is likely to be dry or light. Plan the demo around cached replay scenarios, clearly labelled.
10. **Contract-first build.** Freeze the JSON schemas in hour 1 so the frontend is never blocked on the engine.

## 1. The pitch in one paragraph

CASCADEx takes a 72-hour rainfall forecast with its uncertainty, pushes it through a transparent flood-to-access cascade over Mumbai’s real road and facility geometry, and reports which hospitals, fire stations and settlements lose reachability, when, and how confident we are. It then finds where a limited number of response units should be staged to preserve the most access, and shows the whole chain in a Skylines-style 3D city where every change opens an evidence receipt. Central claim: *a reproducible, uncertainty-aware decision tool that never presents an assumption as a measurement.*

## 2. System pipeline

```
Rainfall forecast (ensemble) ──► online bias correction ──┐
Station history (37 AWS)  ──► rarity percentiles ─────────┤
MCGM / OSM geometry, GHSL ──► zones, roads, facilities ───┼──► Hazard H(z,t)
Source reliability + drift ──► confidence ────────────────┘        │
                                                                     ▼
              Dependency graph (typed edges, lags, evidence labels)
                                                                     ▼
         Monte Carlo cascade: road stress → closures → reachability
                                                                     ▼
        Risk states (hysteresis) + time-to-critical distribution
                                                                     ▼
     Intervention optimizer (budget k) ──► baseline vs plan delta
                                                                     ▼
              Receipts (JSON) ──► Skylines-style 3D UI
```

Heavy computation runs offline in Python at preprocess time. The UI only loads precomputed result files and runs the cheap greedy step live.

## 3. Data: what feeds what, and how to label it

| Source | Feeds | UI label | Honest limit |
| --- | --- | --- | --- |
| Open-Meteo forecast (72h hourly) | Rainfall forcing | FORECAST | Grid cell, not street rain |
| Open-Meteo **Ensemble** API (verify endpoint and models) | Spread across members for uncertainty | FORECAST ENSEMBLE | Frequency of members is not calibrated probability until checked |
| Open-Meteo historical forecasts | Time-correct replays and bias-correction tests | ARCHIVED FORECAST | Check Mumbai coverage and issue-time semantics |
| Mumbai 37-station set (2015–2022) | Rarity percentiles, observed-vs-forecast residuals, rainfall baseline | OBSERVED | Audit timestamps, units, GFS leakage; check data rights |
| MCGM flood spots (344), settlements (346), hospitals, fire stations, shelters, roads, contours | Zones, graph, facilities, exposure | OFFICIAL GIS (static) | Download unverified; sensors are locations, not readings |
| OSM (roads, POIs, `power=substation`, buildings) | Fallback geometry, substation branch, building heights | OSM | Tag quality varies; cache offline |
| GHSL population grid | Population weights | MODELLED POPULATION | State the epoch; aggregate only |
| Tide level (optional, **source unverified**) | Tide-lock factor | MODELLED | Drop if no usable source within 30 minutes |
| 2005 event literature | External stress scenario | STRESS SCENARIO | Not training or test data |

**Tide note.** Mumbai floods are widely linked to heavy rain coinciding with high tide, which hampers drainage outfalls. If you can get predicted tide heights (they are deterministic), a simple “tide-lock” flag that raises hazard when rain overlaps high tide is a very local insight judges will notice. Do not build around it until a data source is confirmed.

## 4. The method, step by step

### 4.1 Rainfall forcing and uncertainty

- Cache the forecast as an immutable named snapshot (fetch time, model, attribution).
- If the ensemble endpoint works, keep every member’s hourly series. If not, use the deterministic series and widen it with a multiplicative spread learned from historical forecast-vs-observed residuals.
- Every number carries a kind tag: observed, forecast, modelled or assumed.

### 4.2 Online bias correction (the genuine online-learning piece)

When observed station rainfall arrives, compare it with what the forecast said for that hour.

- Maintain an exponentially weighted ratio `r_t = EWMA(observed) / EWMA(forecast)` over rolling windows, with a floor so it stays stable in dry spells.
- Apply `r_t` to the remaining forecast hours. No retraining, no stored dataset.
- Run a Page-Hinkley or CUSUM detector on the residuals. When it fires, show a visible **DRIFT** flag (for example, a monsoon-onset base-rate shift) and widen uncertainty for a few hours.
- Prove it by replaying archived forecasts against station data: report MAE with and without correction, plus a persistence baseline.

### 4.3 Hazard Pressure H(z,t)

For each zone z and time t, use only features that actually exist; drop any missing one and lower the confidence instead of filling a value.

- **Rain rarity:** accumulate rainfall over 1, 3, 6, 24, 48 and 72 hours, then convert each to a percentile against the station history. A value of 0.99 means “rarer than 99% of historical windows”. This is data-derived and explainable.
- **Antecedent wetness:** `API_t = k·API_{t−1} + P_t` with hourly decay k set from a configurable time constant (start at 48–72 h as an engineering prior).
- **Hotspot proximity:** distance to MCGM flood spots (see the validation fix in section 6).
- **Low-lying exposure:** zone elevation relative to the minimum within a 500 m buffer, from contours or the DEM. Omit if elevation is unusable.
- **Drainage context:** distance to mapped drainage and hydro lines.
- **Tide-lock flag:** only if a source is confirmed.

`H = Σ wᵢ·fᵢ`, weights in a config file, labelled **relative hazard score**. Run a ±20% weight sensitivity and show whether the top-ranked zones change.

### 4.4 The dependency graph, and how “discovery” is handled honestly

The PS says the dependency structure is not provided. Your answer has two parts.

**Structure from priors and geometry, with every edge labelled by evidence type:**

| Edge | Mechanism | Lag prior | Evidence |
| --- | --- | --- | --- |
| Rainfall → zone hazard | Accumulation and antecedent wetness | 0–3 h | Physical prior |
| Zone hazard → road-edge stress | Spatial overlap of hazard with road | 0–2 h | Mapped geometry |
| Road stress → reachability | Shortest-path recomputation | immediate | Graph computation |
| Reachability loss → response delay | Added route cost | immediate | Graph computation |
| Response delay → hospital pressure | Catchment shift (optional) | 1–6 h | **Assumed** |
| Zone hazard → substation exposure → backup-power flag at shelters and hospitals (optional) | Proximity to hazard | 0–6 h | Geometry plus **assumed** rule |
| Evacuation → egress congestion → reachability | BPR congestion function (feedback) | 0–3 h | Assumed parameters |

Each edge stores a weight, a lag distribution (lognormal) and the evidence label. The UI shows the label on every link in the cascade trace.

**Discovery on simulated streams.** Public data has no joint time series of drainage, traffic and hospitals, so the honest move is a small simulator that generates multi-system streams from a known ground-truth graph.

- Apply lagged partial correlation (or PCMCI-style testing via the open-source `tigramite`, if time allows) **conditioning on rainfall**, so two things that both respond to rain do not get linked.
- Report precision and recall of recovered edges against the known graph, including a deliberate confounder case.
- Policy: a learned-only edge appears in the UI as a **hypothesis** and is never used in counterfactual interventions. Only edges backed by physical prior or geometry are used there.

This answers “infer it from data” without claiming causal discovery from observational data, which is the trap a technically literate judge will probe.

### 4.5 Cascade propagation as Monte Carlo

For each of N samples (start with 100–200):

1. Draw an ensemble member (or a spread-widened deterministic series).
2. Draw scenario parameters from declared ranges: λ in \[1, 4\], exponent p in \[1, 2\], closure threshold θ in \[0.6, 0.9\], and lag jitter.
3. For each horizon bucket (1, 3, 6, 12, 24, 48, 72 h), compute road-edge exposure, then cost `c_e = base_e·(1 + λ·exposure^p)`. Edges above θ are closed.
4. Run multi-source Dijkstra from facilities over the stressed graph. Record which settlements remain within the service cost threshold, and which facilities are isolated.
5. Compute retained access: `100 × Σ P_s·A_s(t) / Σ P_s·A_s(0)`.

**Outputs across samples:**

- Retained access median and P10–P90 per horizon.
- **Time-to-critical distribution:** first bucket where retained access drops below the critical threshold, per sample, summarized as median and P10–P90 (interpolate between buckets and say so).
- “Hospital H isolated in X% of scenarios”.

**Compute budget (verify on your laptop).** Use `scipy.sparse.csgraph` or `igraph`, not pure-Python NetworkX, for the heavy loop. Clip the AOI to roughly 5–20k edges. Rough scale: 7 buckets × 100 samples = 700 graph states; with about 40 candidate staging sites that is about 28,000 single-source runs, which should take minutes, not hours. Store reachability as bitsets so the browser never recomputes shortest paths.

**Feedback loop.** The evacuation toggle adds congestion to egress edges using the standard BPR function: `t = t₀·(1 + 0.15·(v/c)⁴)`. Flow v and capacity c are labelled assumptions. The demo moment: an evacuation helps one area and degrades access in another.

### 4.6 Risk states, confidence and hysteresis

The PS needs NORMAL, WATCH, HIGH RISK and CRITICAL per zone and city-wide. Initial, configurable rules (placeholders to tune, not calibrated):

| State | Zone rule | City rule |
| --- | --- | --- |
| NORMAL | H < 0.30 | Retained access ≥ 95% |
| WATCH | H 0.30–0.50, or ≥20% of members exceed IMD “heavy” (64.5 mm/24 h) | 85–95% |
| HIGH RISK | H 0.50–0.75, or ≥50% of members exceed heavy | 65–85% |
| CRITICAL | H > 0.75 and a facility isolated in ≥50% of samples | < 65%, or any hospital isolated in ≥50% of samples |

**Hysteresis.** Escalate after two consecutive evaluations meeting the condition (immediately if the jump is two levels). De-escalate only after three consecutive lower evaluations and a minimum dwell of three scenario hours. Log every state change with its reason.

**Confidence is separate from risk.** It is the minimum of: fraction of weighted sources that are fresh, ensemble spread (wide means lower), and share of the chain resting on assumed edges. Missing data lowers confidence and never silently lowers risk.

### 4.7 Source reliability and common-cause failures

- Each source has a trust value (Beta posterior) updated by agreement with the independent consensus, plus a freshness decay against its expected cadence.
- Sources are grouped by shared infrastructure (for example, one gateway). A group contributes at most one vote, so 40 silent sensors behind one gateway read as **one group outage**, not 40 “all clear” signals.
- Contradictions (citizen report vs gauge) are shown as CONTRADICTORY and weighted by trust, never averaged away.
- All citizen reports are labelled as simulated fixtures.

### 4.8 Intervention optimizer

- **Action:** stage k response units at candidate existing facilities. Optional pump and evacuation controls use explicit assumed effects shown in the receipt.
- **Objective:** minimize `J = w1·population access loss + w2·high-priority facilities degraded + w3·deployment cost + w4·side-effect penalty`, evaluated as the **mean over samples** and also the **mean of the worst 10%** (CVaR-style) so the plan does not only win in the average case.
- **Algorithm:** greedy with lazy re-evaluation. For a pure coverage objective under fixed scenarios this is a monotone submodular maximization with the classic (1 − 1/e) guarantee; with extra penalty terms treat it as a strong heuristic and do not claim the guarantee.
- **Make the win meaningful:** compare greedy against (a) random placement, (b) nearest-to-hotspot placement, (c) most-populous-area placement. Report gain over each.
- **Assumption sensitivity:** vary λ, p, θ and the service threshold, then report whether the ranking of plans stays the same (rank correlation). A plan that wins only under one assumption set is flagged fragile.

### 4.9 Receipts

Every state change writes a receipt: input snapshot IDs, kind tags, rule version, edges touched, risk and confidence, the change in retained access, and an `unknowns` list. The UI renders receipts as the clickable cascade trace. Templated text generates the explanation, with no free-form LLM.

## 5. The Cities: Skylines-style interface (realistic version)

Yes, it is a good idea, and it is feasible if you borrow the *interaction language* rather than the simulation. Skylines users already understand overlays, coverage radii, time controls and budget panels, which is exactly your decision loop.

| Skylines mechanic | CASCADEx equivalent | Tech | Priority |
| --- | --- | --- | --- |
| Pitched 3D city with zoning colours | Extruded buildings tinted by settlement and land use, pitch about 60° | MapLibre `fill-extrusion` | P0 |
| Info views (water, traffic, health) | Layer picker: Hazard, Access, Confidence, Evidence | MapLibre layers | P0 |
| **Service coverage radius** | Reachability area per facility under the current scenario, **shrinking as roads close** | Precomputed reachability polygons or coloured roads | P0 (the money shot) |
| Pause / 1x / 2x / 3x speed | Play the 72 h timeline at three speeds, plus scrub | Timeline component | P0 |
| Budget and policy panel | Resource budget k, evacuation toggle, scenario picker | React panel | P0 |
| Top resource bar | Retained access %, facilities isolated, confidence, scenario kind | HUD | P0 |
| Advisor notifications | Cascade event toasts: “T+14h: Road edge closes, Hospital X loses direct access”. Click to fly the camera there | Event list from receipts | P1 |
| Moving vehicles | Response units travelling shortest paths, rerouting when an edge closes | deck.gl `TripsLayer` on MapLibre | P1 |
| Disaster trigger | Scenario selector: cached forecast, historical replay, 2005 stress test, synthetic extreme | Config | P0 |
| Realistic flood water | **Do not do this.** It implies measured depth. Use edge stress colours and closure icons | n/a | Never |

**Stack:** MapLibre GL JS plus deck.gl (interleaved overlay), bundled from npm so it works offline, with local GeoJSON or PMTiles and local fonts. Building heights from MCGM or OSM `building:levels` where present, otherwise a neutral height labelled approximate.

**Effort:** P0 fits the 14:00–18:00 UI slot in the blueprint. P1 only after the engine gate passes. If the coverage-shrink view works, the Skylines feel is mostly achieved.

**Visual rules:** risk colour and confidence hatching are separate channels; every number shows its kind tag; a persistent footer says “advisory prototype, modelled outputs”.

## 6. Evaluation plan

1. **Rainfall:** chronological split (for example train 2015–2020, tune 2021, test 2022 as coverage allows). Compare raw forecast, bias-corrected forecast and persistence on MAE, RMSE and heavy-rain precision/recall. Fit all normalizers on training data only.
2. **Ensemble reliability:** for archived forecasts, plot how often “≥X% of members exceed heavy” actually verified. Only if the curve looks reasonable may you say “calibrated”, and only for rainfall exceedance.
3. **Hotspot plausibility without circularity:** hold out about 30% of flood spots by spatial block, build the hazard score without them, and report where held-out spots rank (top-k overlap). Never validate on spots that were used as features.
4. **Ablations:** remove each hazard feature and show the effect on held-out rank.
5. **Cascade tests:** scripted scenarios with known disconnections; the engine must find them. Label as synthetic stress tests.
6. **Intervention value:** same scenario, budget and threshold, with and without; report the gain over random, hotspot-nearest and population-first baselines, plus rank stability.
7. **Red team:** 60% of feeds missing, one gateway group outage, a late duplicate, a retraction, and a contradictory report. Check no crash, confidence falls, no spurious state flips.
8. **Leakage tests:** an automated test asserting no input timestamp is later than the prediction issue time.
9. **Generalization:** hold out one ward or catchment, swap the AOI config, and run the pipeline unchanged. State clearly this is software generalization, not cross-city calibration.

## 7. PS 2.2 scorecard (honest)

| PS requirement | What we do | Strength |
| --- | --- | --- |
| Four risk states, per zone and city | Section 4.6 | Strong |
| Multi-horizon, time-to-critical | Buckets plus Monte Carlo distribution | Strong for the flood branch |
| Dependency discovery | Priors plus simulated-stream discovery with confounder control | Partial, honestly framed |
| Cascade with branching and feedback | Flood→access core, evacuation loop, optional branches | Partial |
| Online learning under drift | Online bias correction, drift flag, reliability updates | Partial to strong |
| Missing and adversarial inputs | Source groups, confidence, red-team fixtures | Strong on tested cases |
| Causal explainability | Receipts with evidence-labelled edges | Strong |
| Constrained counterfactuals with side effects | Greedy under budget, BPR side effects, robustness | Strong |
| Generalization to unseen city | Config swap and held-out ward | Weak to partial |
| Temporal validation | Chronological rainfall test, leakage test | Strong for rainfall; none for cascade outcomes, said openly |

## 8. Schedule adjustments (event day)

Keep the blueprint’s 24-hour plan, with these changes:

- **Hour 0–1:** besides the data audit, freeze the JSON contracts (zones, edges, receipts, plans) and give the frontend a hand-written fake scenario. Both streams then run in parallel.
- **Hour 0–1:** pull and cache *both* a current 72 h snapshot and a historical heavy-rain replay with its archived forecast. Decide the demo scenario now.
- **Cut line:** if the MCGM layers fail by hour 2, switch to OSM geometry and drop official-layer claims. If the ensemble API fails, use the widened deterministic series.
- **Do last, only if time remains:** vehicles, tide-lock, power and hospital-surge branches, `tigramite`.

## 9. Demo tweaks (four minutes)

1. Open the 3D city; state the cascade idea in one sentence (30 s).
2. Press play at 3x on the replay scenario. Coverage areas around hospitals visibly **shrink** as roads close, with advisor toasts firing (60 s).
3. Click a toast; the cascade trace shows each link with its evidence label and the time-to-critical range (45 s).
4. Set k = 2; compare baseline vs plan, show the gain over naive placements and the rank-stability note (45 s).
5. Toggle evacuation; show the helpful-but-harmful side effect (20 s).
6. Inject the gateway outage; confidence drops and unknown areas hatch; the risk number does not fall (20 s).
7. Show the validation slide, including what is *not* validated (20 s).

## 10. Risks the blueprint underplays, and questions for the event leads

- **Assumption-dominated output.** The closure parameters drive the result. The mitigation is the sensitivity and rank-stability report, shown in the UI.
- **Population layer failure** would turn “people” into “settlement polygons”. Decide early and say which.
- **Ensemble availability for Mumbai** is unverified. Confirm in the first hour.
- **Judging format unknown.** Ask Arnav Bansal or Rakshit Jain whether judging is a live demo or replay, whether organizers supply data or a stream format, and what a “zone” means. If the organizers hand over their own stream, the adapter layer must ingest it without engine changes.
- **Scope creep.** Every extra branch must carry an evidence label or it does not ship.

## 11. What is not verified

I could not download or test any source from here. MCGM layer export, the rainfall zip contents, the Open-Meteo ensemble and historical-forecast coverage for Mumbai, tide data, and the runtime estimates in 4.5 are all unverified until your team tests them. The IMD rainfall class threshold (64.5 mm/24 h for heavy) comes from my own knowledge; confirm it against the IMD reference before putting it on a slide.
