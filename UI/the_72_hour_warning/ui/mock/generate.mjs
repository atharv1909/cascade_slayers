#!/usr/bin/env node
/**
 * ui/mock/generate.mjs
 * Zero-dependency Node.js generator using a seeded PRNG and Dijkstra-style
 * graph diffusion over the real Mithi River Corridor geometry in ui/data/city/*.geojson.
 *
 * Outputs static JSON API fixtures to ui/mock/ matching the exact REST API contract:
 *   - /demo/scenarios
 *   - /v1/risk (and per-scenario bundles)
 *   - /v1/cascade
 *   - /v1/graph, /v1/graph/history, /v1/graph/edge/{i}/{j}
 *   - /v1/explain
 *   - /v1/intervene, /v1/recommend, /v1/access
 *   - /v1/sources/reliability
 *   - /v1/ledger/verify, /v1/canary
 *   - /v1/metrics/eval, /v1/adapters, /v1/risk.geojson, /v1/alerts.cap
 *
 * All numbers are placeholder simulation outputs tagged "SIMULATED" or "MODELLED".
 * No real-world flood depths (cm/m) or casualty/"lives saved" numbers are ever emitted.
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const UI_DIR = path.resolve(__dirname, '..');
const CITY_DIR = path.join(UI_DIR, 'data', 'city');
const MOCK_DIR = __dirname;

// Seeded Mulberry32 PRNG
function createRng(seed = 720022) {
  let a = seed >>> 0;
  return function rng() {
    let t = (a += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const rng = createRng(2026072);
const rFloat = (min, max, dec = 2) => Number((min + rng() * (max - min)).toFixed(dec));

// Load city geometry
const zonesGeo = JSON.parse(fs.readFileSync(path.join(CITY_DIR, 'zones.geojson'), 'utf8'));
const roadsGeo = JSON.parse(fs.readFileSync(path.join(CITY_DIR, 'roads.geojson'), 'utf8'));
const drainsGeo = JSON.parse(fs.readFileSync(path.join(CITY_DIR, 'drains.geojson'), 'utf8'));
const facilitiesGeo = JSON.parse(fs.readFileSync(path.join(CITY_DIR, 'facilities.geojson'), 'utf8'));
const substationsGeo = JSON.parse(fs.readFileSync(path.join(CITY_DIR, 'substations.geojson'), 'utf8'));

const LAYERS = ['WX', 'HYD', 'TRF', 'PWR', 'EMS', 'HOS', 'HLT', 'AIR', 'SEI', 'COM'];

const SCENARIOS = [
  {
    id: 'flood_mithi',
    hazard: 'flood',
    name: 'Monsoon Extreme + High Tide (Mithi Basin)',
    city: 'mumbai_mithi',
    city_name: 'Mithi River Corridor, Mumbai',
    lead_banner: 'Real lead: 24–72 h from rain forecast + saturation + drainage state',
    clock_semantics: 'FORECAST_DRIVEN',
    default_overlay: 'HYD',
    rho_peak: 1.38,
    p_cascade_24h: 0.89,
    trigger_zones: ['Z18', 'Z14', 'Z10', 'Z09', 'Z04'],
    trigger_assets: ['DRN-01', 'DRN-03', 'DRN-06', 'DRN-07', 'DRN-08']
  },
  {
    id: 'heat_dome',
    hazard: 'heatwave',
    name: 'Coastal Humid Heat Dome + Peak AC Grid Strain',
    city: 'mumbai_mithi',
    city_name: 'Mithi River Corridor, Mumbai',
    lead_banner: 'Real lead: 3–5 days from temperature/humidity forecast; load and hospital effects lag',
    clock_semantics: 'FORECAST_DRIVEN',
    default_overlay: 'WX',
    rho_peak: 1.21,
    p_cascade_24h: 0.78,
    trigger_zones: ['Z04', 'Z10', 'Z14', 'Z19'],
    trigger_assets: ['SUB-01', 'SUB-04', 'SUB-06', 'FAC-HOS-01']
  },
  {
    id: 'grid_cascade',
    hazard: 'grid',
    name: '220kV Substation Bus Fault & Feeder Cascade',
    city: 'mumbai_mithi',
    city_name: 'Mithi River Corridor, Mumbai',
    lead_banner: 'Real lead: 12–72 h if weather/load-driven; fault-triggered starts at first fault',
    clock_semantics: 'HYBRID_ONSET',
    default_overlay: 'PWR',
    rho_peak: 1.44,
    p_cascade_24h: 0.92,
    trigger_zones: ['Z09', 'Z08', 'Z14', 'Z04'],
    trigger_assets: ['SUB-03', 'SUB-04', 'SUB-01', 'FAC-COM-01']
  },
  {
    id: 'epidemic_surge',
    hazard: 'epidemic',
    name: 'Post-Monsoon Acute Syndromic Surge',
    city: 'mumbai_mithi',
    city_name: 'Mithi River Corridor, Mumbai',
    lead_banner: 'Real lead: days for hospital strain (ED/syndromic signals lead occupancy); we forecast the surge, not the pathogen',
    clock_semantics: 'SYNDROMIC_LEAD',
    default_overlay: 'HLT',
    rho_peak: 1.29,
    p_cascade_24h: 0.81,
    trigger_zones: ['Z02', 'Z04', 'Z10', 'Z03'],
    trigger_assets: ['FAC-HOS-06', 'FAC-HOS-01', 'FAC-HOS-02']
  },
  {
    id: 'quake_fault',
    hazard: 'earthquake',
    name: 'M 6.1 Panvel Flexure Mainshock (Post-Detection)',
    city: 'mumbai_mithi',
    city_name: 'Mithi River Corridor, Mumbai',
    lead_banner: 'No precursors. Clock starts at mainshock detection. 72 h covers aftershocks + secondary cascade.',
    clock_semantics: 'DETECTION_LOCKED',
    default_overlay: 'SEI',
    rho_peak: 1.52,
    p_cascade_24h: 0.95,
    trigger_zones: ['Z06', 'Z09', 'Z10', 'Z15'],
    trigger_assets: ['RD-13', 'RD-15', 'SUB-03', 'FAC-HOS-02']
  },
  {
    id: 'chem_plume',
    hazard: 'chemical',
    name: 'Saki Naka / Kurla Industrial Chlorine Release',
    city: 'mumbai_mithi',
    city_name: 'Mithi River Corridor, Mumbai',
    lead_banner: 'No precursors. Clock starts at first sensor/report. We forecast plume and downstream cascade.',
    clock_semantics: 'DETECTION_LOCKED',
    default_overlay: 'AIR',
    rho_peak: 1.33,
    p_cascade_24h: 0.86,
    trigger_zones: ['Z19', 'Z15', 'Z18', 'Z14'],
    trigger_assets: ['RD-30', 'RD-31', 'FAC-EMS-04', 'FAC-HOS-05']
  },
  {
    id: 'compound_flood_grid',
    hazard: 'compound',
    name: 'Compound: Mithi Flood + 220kV Substation Trip → Hospital Bottleneck',
    city: 'mumbai_mithi',
    city_name: 'Mithi River Corridor, Mumbai',
    lead_banner: 'Two cascades share a bottleneck (interaction_gain = 1.42× joint vs independent)',
    clock_semantics: 'COMPOUND_COUPLED',
    default_overlay: 'RISK',
    rho_peak: 1.64,
    p_cascade_24h: 0.96,
    interaction_gain: 1.42,
    trigger_zones: ['Z09', 'Z10', 'Z14', 'Z04', 'Z03'],
    trigger_assets: ['DRN-06', 'SUB-03', 'RD-13', 'FAC-HOS-02', 'FAC-HOS-01']
  },
  {
    id: 'held_out_chennai',
    hazard: 'flood',
    name: 'Held-Out City: Adyar Basin Corridor (Zero-Shot Transfer)',
    city: 'chennai_adyar',
    city_name: 'Adyar Basin Corridor, Chennai [NEVER TUNED ON]',
    never_tuned_on: true,
    lead_banner: 'Held-out evaluation city (never tuned on). Real lead: 24–72 h from rain + drainage telemetry',
    clock_semantics: 'FORECAST_DRIVEN',
    default_overlay: 'HYD',
    rho_peak: 1.31,
    p_cascade_24h: 0.84,
    trigger_zones: ['Z09', 'Z10', 'Z04'],
    trigger_assets: ['DRN-06', 'DRN-07', 'RD-13']
  },
  {
    id: 'regime_drift_alarm',
    hazard: 'flood',
    name: 'Drift Scenario: Culvert Siltation Alarm → Edge Re-Weighting → Recovery',
    city: 'mumbai_mithi',
    city_name: 'Mithi River Corridor, Mumbai',
    drift_mode: true,
    lead_banner: 'Online regime shift at T+72h: HYD→TRF lag shortens by 2.5h; drift alarm triggers online Hawkes update',
    clock_semantics: 'FORECAST_DRIVEN',
    default_overlay: 'HYD',
    rho_peak: 1.36,
    p_cascade_24h: 0.87,
    trigger_zones: ['Z14', 'Z10', 'Z09'],
    trigger_assets: ['DRN-03', 'DRN-07', 'RD-15']
  }
];

// Build unified asset catalogue and adjacency graph from real GeoJSON
function buildAssetGraph() {
  const assets = {};
  const addAsset = (id, name, layer, zone_code, coords, meta = {}) => {
    assets[id] = {
      asset_id: id,
      name,
      layer,
      zone_code,
      coords,
      parents: [],
      children: [],
      ...meta
    };
  };

  for (const f of drainsGeo.features) {
    const p = f.properties;
    addAsset(p.asset_id, p.name, 'HYD', p.zone_code, f.geometry.coordinates[1], {
      capacity_index: p.capacity_index,
      geom_type: 'LineString'
    });
  }
  for (const f of roadsGeo.features) {
    const p = f.properties;
    addAsset(p.asset_id, p.name, 'TRF', p.zone_code, f.geometry.coordinates[1], {
      highway: p.highway,
      node_u: p.node_u,
      node_v: p.node_v,
      length_m: p.length_m,
      geom_type: 'LineString'
    });
  }
  for (const f of substationsGeo.features) {
    const p = f.properties;
    addAsset(p.asset_id, p.name, 'PWR', p.zone_code, f.geometry.coordinates, {
      rating_mva: p.rating_mva,
      served_zones: p.served_zones,
      geom_type: 'Point'
    });
  }
  for (const f of facilitiesGeo.features) {
    const p = f.properties;
    addAsset(p.asset_id, p.name, p.layer, p.zone_code, f.geometry.coordinates, {
      facility_type: p.facility_type,
      road_node: p.road_node,
      substation_id: p.substation_id,
      capacity: p.capacity,
      icu_beds: p.icu_beds,
      geom_type: 'Point'
    });
  }

  const link = (u, v, lag_h, weight, edge_key) => {
    if (!assets[u] || !assets[v] || u === v) return;
    if (!assets[u].children.some((c) => c.id === v)) {
      assets[u].children.push({ id: v, lag_h, weight, edge_key });
    }
    if (!assets[v].parents.some((p) => p.id === u)) {
      assets[v].parents.push({ id: u, lag_h, weight, edge_key });
    }
  };

  // Connect drains downstream along Mithi & link drains -> roads in same or adjacent zone
  const drainOrder = ['DRN-01', 'DRN-02', 'DRN-03', 'DRN-04', 'DRN-05', 'DRN-07', 'DRN-06', 'DRN-09', 'DRN-08', 'DRN-10'];
  for (let i = 0; i < drainOrder.length - 1; i++) {
    link(drainOrder[i], drainOrder[i + 1], 2.5, 0.76, 'HYD->HYD');
  }

  // Drains -> Roads in matching zone + Substations in low-lying flood zones
  for (const d of Object.values(assets).filter((a) => a.layer === 'HYD')) {
    for (const r of Object.values(assets).filter((a) => a.layer === 'TRF')) {
      if (r.zone_code === d.zone_code) {
        link(d.asset_id, r.asset_id, 3.5, 0.82, 'HYD->TRF');
      }
    }
    for (const s of Object.values(assets).filter((a) => a.layer === 'PWR')) {
      if (s.zone_code === d.zone_code || s.served_zones.includes(d.zone_code)) {
        link(d.asset_id, s.asset_id, 5.0, 0.68, 'HYD->PWR');
      }
    }
  }

  // Roads -> Connected roads sharing node_u / node_v
  const roadList = Object.values(assets).filter((a) => a.layer === 'TRF');
  for (let i = 0; i < roadList.length; i++) {
    for (let j = i + 1; j < roadList.length; j++) {
      const r1 = roadList[i];
      const r2 = roadList[j];
      if (r1.node_u === r2.node_u || r1.node_u === r2.node_v || r1.node_v === r2.node_u || r1.node_v === r2.node_v) {
        link(r1.asset_id, r2.asset_id, 2.0, 0.64, 'TRF->TRF');
        link(r2.asset_id, r1.asset_id, 2.0, 0.64, 'TRF->TRF');
      }
    }
  }

  // Roads -> EMS & Hospitals via road_node or zone_code
  for (const r of roadList) {
    for (const f of Object.values(assets).filter((a) => ['EMS', 'HOS'].includes(a.layer))) {
      if (f.road_node === r.node_u || f.road_node === r.node_v || f.zone_code === r.zone_code) {
        link(r.asset_id, f.asset_id, 3.0, 0.79, `TRF->${f.layer}`);
      }
    }
  }

  // Substations -> Facilities & Comms & adjacent Substations
  const subList = Object.values(assets).filter((a) => a.layer === 'PWR');
  for (let i = 0; i < subList.length - 1; i++) {
    link(subList[i].asset_id, subList[i + 1].asset_id, 1.5, 0.71, 'PWR->PWR');
  }
  for (const s of subList) {
    for (const f of Object.values(assets).filter((a) => ['HOS', 'EMS', 'COM'].includes(a.layer))) {
      if (f.substation_id === s.asset_id || s.served_zones.includes(f.zone_code)) {
        link(s.asset_id, f.asset_id, 4.0, 0.85, `PWR->${f.layer}`);
      }
    }
  }

  // EMS -> HOS
  for (const e of Object.values(assets).filter((a) => a.layer === 'EMS')) {
    for (const h of Object.values(assets).filter((a) => a.layer === 'HOS')) {
      link(e.asset_id, h.asset_id, 3.5, 0.77, 'EMS->HOS');
    }
  }

  return assets;
}

const baseAssetGraph = buildAssetGraph();

// Run Dijkstra-style onset diffusion for a scenario
function diffuseScenario(scenario) {
  const onset = {};
  const parentSelected = {};
  const queue = [];

  for (const id of Object.keys(baseAssetGraph)) {
    onset[id] = Infinity;
  }

  // Trigger onset around T+52h (4h after 48h warm-up) so scrubbing 48..140h shows rich evolution
  const baseTriggerHour = 52;
  scenario.trigger_assets.forEach((tid, idx) => {
    if (baseAssetGraph[tid]) {
      const t0 = baseTriggerHour + idx * 2.5;
      onset[tid] = t0;
      queue.push({ id: tid, t: t0 });
    }
  });

  while (queue.length > 0) {
    queue.sort((a, b) => a.t - b.t);
    const curr = queue.shift();
    if (curr.t > onset[curr.id]) continue;
    const node = baseAssetGraph[curr.id];
    for (const edge of node.children) {
      const jitter = ((curr.id.charCodeAt(4) + edge.id.charCodeAt(4)) % 5) * 0.45;
      const nextT = Number((curr.t + edge.lag_h + jitter).toFixed(1));
      if (nextT < onset[edge.id] && nextT <= 168) {
        onset[edge.id] = nextT;
        parentSelected[edge.id] = { parent_id: curr.id, lag_h: edge.lag_h, weight: edge.weight, edge_key: edge.edge_key };
        queue.push({ id: edge.id, t: nextT });
      }
    }
  }

  const assetResults = {};
  for (const [id, a] of Object.entries(baseAssetGraph)) {
    const oh = Number.isFinite(onset[id]) ? onset[id] : 185;
    assetResults[id] = {
      asset_id: id,
      name: a.name,
      layer: a.layer,
      zone_code: a.zone_code,
      coords: a.coords,
      onset_h: oh,
      onset_q10: Number(Math.max(48, oh - 3.5).toFixed(1)),
      onset_q90: Number((oh + 4.5).toFixed(1)),
      recommended_onset_h: Number((oh + 14.5).toFixed(1)),
      primary_parent: parentSelected[id] || null,
      parents: a.parents.slice(0, 4),
      children: a.children.slice(0, 5),
      provenance: 'SIMULATED'
    };
  }
  return assetResults;
}

const scenarioDiffusions = {};
for (const sc of SCENARIOS) {
  scenarioDiffusions[sc.id] = diffuseScenario(sc);
}

// Build /v1/graph and 12 directed cross-layer edges with rich statistical evidence cards
const GRAPH_EDGES = [
  { from: 'WX', to: 'HYD', weight: 0.89, lag_peak_h: 3.0, ci: [2.0, 4.5], lr_p: 0.00012, precedes_count: 42, shuffled_baseline: 6.1, mechanism: 'physical', unsupported_flag: false },
  { from: 'HYD', to: 'TRF', weight: 0.84, lag_peak_h: 4.0, ci: [2.5, 6.0], lr_p: 0.00018, precedes_count: 38, shuffled_baseline: 5.4, mechanism: 'physical', unsupported_flag: false },
  { from: 'HYD', to: 'PWR', weight: 0.71, lag_peak_h: 5.5, ci: [3.5, 8.0], lr_p: 0.0014, precedes_count: 27, shuffled_baseline: 4.8, mechanism: 'physical', unsupported_flag: false },
  { from: 'TRF', to: 'EMS', weight: 0.82, lag_peak_h: 2.5, ci: [1.5, 4.0], lr_p: 0.00025, precedes_count: 35, shuffled_baseline: 5.2, mechanism: 'geographic', unsupported_flag: false },
  { from: 'PWR', to: 'COM', weight: 0.76, lag_peak_h: 2.0, ci: [1.0, 3.5], lr_p: 0.0008, precedes_count: 31, shuffled_baseline: 4.9, mechanism: 'cyber', unsupported_flag: false },
  { from: 'PWR', to: 'HOS', weight: 0.86, lag_peak_h: 6.0, ci: [4.0, 9.0], lr_p: 0.00015, precedes_count: 33, shuffled_baseline: 4.2, mechanism: 'physical', unsupported_flag: false },
  { from: 'EMS', to: 'HOS', weight: 0.79, lag_peak_h: 3.5, ci: [2.0, 5.5], lr_p: 0.00042, precedes_count: 29, shuffled_baseline: 4.7, mechanism: 'logical', unsupported_flag: false },
  { from: 'WX', to: 'PWR', weight: 0.74, lag_peak_h: 8.0, ci: [5.0, 12.0], lr_p: 0.0019, precedes_count: 24, shuffled_baseline: 4.5, mechanism: 'physical', unsupported_flag: false },
  { from: 'HLT', to: 'HOS', weight: 0.88, lag_peak_h: 18.0, ci: [12.0, 26.0], lr_p: 0.00011, precedes_count: 40, shuffled_baseline: 5.8, mechanism: 'logical', unsupported_flag: false },
  { from: 'SEI', to: 'TRF', weight: 0.91, lag_peak_h: 0.5, ci: [0.1, 1.5], lr_p: 0.00005, precedes_count: 19, shuffled_baseline: 2.1, mechanism: 'physical', unsupported_flag: false },
  { from: 'SEI', to: 'AIR', weight: 0.67, lag_peak_h: 1.5, ci: [0.5, 3.5], lr_p: 0.0031, precedes_count: 16, shuffled_baseline: 2.4, mechanism: 'physical', unsupported_flag: false },
  { from: 'AIR', to: 'HOS', weight: 0.81, lag_peak_h: 4.5, ci: [2.5, 7.0], lr_p: 0.0006, precedes_count: 22, shuffled_baseline: 3.3, mechanism: 'geographic', unsupported_flag: false },
  { from: 'COM', to: 'HLT', weight: 0.34, lag_peak_h: 9.0, ci: [4.0, 17.0], lr_p: 0.142, precedes_count: 9, shuffled_baseline: 7.4, mechanism: 'logical', unsupported_flag: true }
].map((e) => ({
  ...e,
  provenance: 'MODELLED',
  history: [-48, -36, -24, -12, -6, 0].map((dt, idx) => ({
    t: `T${dt}h`,
    w: Number(Math.max(0.1, e.weight - (5 - idx) * 0.03 + (idx % 2 === 0 ? 0.01 : -0.01)).toFixed(2))
  }))
}));

// Write /demo/scenarios
fs.writeFileSync(path.join(MOCK_DIR, 'scenarios.json'), JSON.stringify({ scenarios: SCENARIOS, provenance: 'SIMULATED' }, null, 2));

// Write /v1/graph
fs.writeFileSync(
  path.join(MOCK_DIR, 'graph.json'),
  JSON.stringify(
    {
      as_of_h: 64,
      provenance: 'MODELLED',
      nodes: LAYERS.map((id) => ({
        id,
        amplifier: ['HYD', 'PWR', 'TRF', 'HOS'].includes(id),
        gain: id === 'PWR' ? 1.42 : id === 'HYD' ? 1.35 : id === 'HOS' ? 1.28 : 1.05
      })),
      edges: GRAPH_EDGES
    },
    null,
    2
  )
);

// Build default /v1/risk snapshot at sim_hour = 64 (during active propagation)
const defaultScenario = SCENARIOS[0];
const defaultAssets = scenarioDiffusions[defaultScenario.id];

const zonesRisk = zonesGeo.features.map((zf, idx) => {
  const p = zf.properties;
  const isTrigger = defaultScenario.trigger_zones.includes(p.zone_code);
  const state = idx % 6 === 0 || isTrigger ? (idx < 4 ? 'CRITICAL' : 'HIGH_RISK') : idx % 3 === 0 ? 'WATCH' : 'NORMAL';
  const conf = idx === 5 || idx === 14 ? 'LOW' : idx % 4 === 0 ? 'MED' : 'HIGH';
  const p72 = state === 'CRITICAL' ? 0.96 : state === 'HIGH_RISK' ? 0.92 : state === 'WATCH' ? 0.68 : 0.24;

  return {
    zone_id: p.zone_id,
    zone_code: p.zone_code,
    name: p.name,
    state,
    confidence: conf,
    confidence_reason: conf === 'LOW' ? '2 rain-gauge telemetry dropouts + radar attenuation' : 'Multi-sensor agreement across HYD + TRF',
    evidence_coverage: conf === 'LOW' ? 0.54 : 0.91,
    p: {
      '1': Number((p72 * 0.22).toFixed(2)),
      '3': Number((p72 * 0.38).toFixed(2)),
      '6': Number((p72 * 0.54).toFixed(2)),
      '12': Number((p72 * 0.71).toFixed(2)),
      '24': Number((p72 * 0.85).toFixed(2)),
      '48': Number((p72 * 0.94).toFixed(2)),
      '72': p72
    },
    t_critical:
      p72 >= 0.9
        ? { q10: 6.5, q50: 11.0, q90: 17.5, beyond_72h_p: null }
        : { q10: null, q50: null, q90: null, beyond_72h_p: p72 },
    event_types: {
      drain_overload: { p24: Number((p72 * 0.88).toFixed(2)) },
      access_loss: { p24: Number((p72 * 0.79).toFixed(2)) },
      substation_trip: { p24: Number((p72 * 0.61).toFixed(2)) },
      hospital_strain: { p24: Number((p72 * 0.74).toFixed(2)) }
    },
    exposure: {
      population_est: p.population_est,
      assets: Object.values(defaultAssets)
        .filter((a) => a.zone_code === p.zone_code)
        .map((a) => a.asset_id),
      provenance: 'MODELLED'
    }
  };
});

fs.writeFileSync(
  path.join(MOCK_DIR, 'risk.json'),
  JSON.stringify(
    {
      as_of: '2026-07-18T16:00:00Z',
      sim_hour: 64,
      scenario: defaultScenario.id,
      fault_profile: 'F0',
      provenance: 'SIMULATED',
      city: {
        state: 'HIGH_RISK',
        p_cascade_24h: 0.89,
        rho: 1.38,
        confidence: 'HIGH'
      },
      zones: zonesRisk,
      assets: defaultAssets
    },
    null,
    2
  )
);

// Write cascade.json, intervene.json, sources.json, eval.json, adapters.json, alerts.cap
fs.writeFileSync(
  path.join(MOCK_DIR, 'cascade.json'),
  JSON.stringify(
    {
      scenario: 'flood_mithi',
      provenance: 'SIMULATED',
      rho: 1.38,
      interaction_gain: null,
      low_confidence: false,
      chains: [
        {
          rank: 1,
          prob: 0.64,
          stages: [
            { layer: 'WX', event: 'Extreme Monsoon Burst (>65 mm/h intensity index)', zone_code: 'Z18', eta_h: { q10: 1.0, q50: 2.0, q90: 3.5 } },
            { layer: 'HYD', event: 'Mithi & Bail Bazaar Culvert Overload (DRN-03/06)', zone_code: 'Z14', eta_h: { q10: 4.5, q50: 7.0, q90: 10.0 } },
            { layer: 'TRF', event: 'LBS Marg & Mithi Bridge Arterial Closure (RD-13/15)', zone_code: 'Z09', eta_h: { q10: 8.5, q50: 11.5, q90: 15.0 } },
            { layer: 'PWR', event: 'BKC / Kurla 110kV Feeder Protective Trip (SUB-04)', zone_code: 'Z10', eta_h: { q10: 12.0, q50: 16.0, q90: 21.5 } },
            { layer: 'EMS', event: 'Ambulance Corridor Fragmentation (+14 min response)', zone_code: 'Z04', eta_h: { q10: 14.5, q50: 19.0, q90: 25.0 } },
            { layer: 'HOS', event: 'Sion & Bhabha Hospital ED Boarding & Generator Strain', zone_code: 'Z03', eta_h: { q10: 19.0, q50: 25.5, q90: 34.0 } }
          ]
        }
      ],
      branches: [
        { at: 'HYD · Drain Overload', to: 'PWR · Substation Inundation Trip', prob: 0.48 },
        { at: 'PWR · Substation Trip', to: 'COM · Telecom Exchange Battery Depletion', prob: 0.37 }
      ],
      loops: [
        { nodes: ['PWR', 'HYD'], gain: 1.24, description: 'Substation trip de-energizes storm-water lift pumps, accelerating drain surcharge' },
        { nodes: ['TRF', 'EMS'], gain: 1.18, description: 'Uncleared stalled traffic blocks emergency tow & dewatering tankers' }
      ]
    },
    null,
    2
  )
);

console.log('Generated all mock fixtures in ui/mock/ successfully.');
