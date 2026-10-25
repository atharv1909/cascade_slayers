/**
 * ui/app/api.js
 * Unified API client module for "The 72-Hour Warning".
 * Switching from mock data to the real backend requires changing ONLY window.CONFIG.API_BASE.
 */

export const getApiBase = () => (window.CONFIG && window.CONFIG.API_BASE) ? window.CONFIG.API_BASE : './mock';
export const isMockMode = () => getApiBase().includes('mock');

async function request(endpoint, options = {}) {
  const base = getApiBase().replace(/\/$/, '');
  if (isMockMode()) {
    // Map REST endpoints to static mock fixtures in ui/mock/ when running offline
    const clean = endpoint.split('?')[0];
    let file = 'risk.json';
    if (clean.includes('/demo/scenarios')) file = 'scenarios.json';
    else if (clean.includes('/v1/cascade')) file = 'cascade.json';
    else if (clean.includes('/v1/graph')) file = 'graph.json';
    const res = await fetch(`${base}/${file}`);
    return res.json();
  }
  const res = await fetch(`${base}${endpoint}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${endpoint}`);
  return res.json();
}

export const API = {
  getScenarios: () => request('/demo/scenarios'),
  setScenario: (id, city, fault_profile) => request('/demo/scenario', { method: 'POST', body: JSON.stringify({ id, city, fault_profile }) }),
  setSpeed: (x) => request('/demo/speed', { method: 'POST', body: JSON.stringify({ x }) }),
  seek: (as_of) => request('/demo/seek', { method: 'POST', body: JSON.stringify({ as_of }) }),
  pause: () => request('/demo/pause', { method: 'POST' }),
  play: () => request('/demo/play', { method: 'POST' }),
  setFault: (profile) => request('/demo/fault', { method: 'POST', body: JSON.stringify({ profile }) }),
  getRisk: (as_of, zone = '') => request(`/v1/risk?as_of=${encodeURIComponent(as_of)}&zone=${encodeURIComponent(zone)}`),
  getCascade: (target = 'city') => request(`/v1/cascade?zone=${encodeURIComponent(target)}`),
  getGraph: () => request('/v1/graph'),
  getGraphHistory: () => request('/v1/graph/history'),
  getEdgeEvidence: (i, j) => request(`/v1/graph/edge/${encodeURIComponent(i)}/${encodeURIComponent(j)}`),
  getExplain: (zone, layer, as_of) => request(`/v1/explain?zone=${zone}&layer=${layer}&as_of=${as_of}`),
  intervene: (payload) => request('/v1/intervene', { method: 'POST', body: JSON.stringify(payload) }),
  getRecommend: () => request('/v1/recommend'),
  getAccess: () => request('/v1/access'),
  getSourcesReliability: () => request('/v1/sources/reliability'),
  verifyLedger: () => request('/v1/ledger/verify'),
  runCanary: () => request('/v1/canary'),
  getEvalMetrics: () => request('/v1/metrics/eval'),
  getAdapters: () => request('/v1/adapters'),
  ingestLiveFeed: (payload) => request('/v1/ingest', { method: 'POST', body: JSON.stringify(payload) }),
  getRiskGeoJSON: () => request('/v1/risk.geojson')
};
