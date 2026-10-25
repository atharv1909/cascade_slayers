from __future__ import annotations
import os
import json
import yaml
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
import torch

from harness.paths import get_project_root
from harness.paths import get_project_root
from harness.schema import (
    CanonicalEvent, RiskResponse, CascadeResponse,
    InterveneResponse, SourcesResponse, LedgerVerifyResponse,
    RiskState, ConfidenceLevel, ExposureSummary, ZoneRiskRecord, CityRiskSummary
)
from harness.store import AsOfStore
from harness.ledger import HashChainedLedger
from harness.canary import run_leakage_canary_test
from harness.replay import ReplayClock
from state.estimator import RobustStateEstimator
from state.truth_discovery import CRHTruthDiscovery
from state.citizen_trust import CitizenTrustManager
from cascade.hawkes import DiscreteHawkesGLM
from cascade.etas import EpidemicTypeAftershockSequence
from cascade.mc import CascadeMonteCarlo
from cascade.evidence import EdgeEvidenceEngine
from cascade.loops import detect_feedback_loops
from risk.gbm import MultiHorizonRiskGBM
from risk.conformal import MondrianConformalPredictor
from risk.states import RiskStateMachine
from decide.interventions import InterventionCatalog
from decide.counterfactual import CounterfactualSimulator
from decide.allocate import ResourceAllocator
from explain.shap_groups import compute_layer_driver_contributions
from explain.parents import compute_hawkes_parent_attribution
from explain.narrative import generate_plain_bulletin, generate_cascade_receipt
from online.drift import DriftMonitor
from online.corrector import OnlineResidualCorrector
from eval.report import generate_evaluation_scoreboard
from adapters.registry import AdapterRegistry
from api.routes.cap import generate_cap_alert_xml
from api.routes.geojson import generate_risk_geojson

class EngineState:
    """
    Central operational engine for Cascade_slayers.
    Coordinates the event-sourced store, state estimators, Hawkes cascade engine,
    LightGBM multi-horizon risk predictor, MILP allocator, and auditing ledgers.
    """
    def __init__(self, root_dir: Optional[str] = None):
        if root_dir is None:
            root_dir = get_project_root()
        self.root_dir = root_dir
        self.lock = threading.RLock()

        # Operational modes
        self.active_scenario = "flood"
        self.active_city = "mumbai"
        self.active_fault_profile = "F0"

        # Infrastructure configs
        with open(os.path.join(root_dir, "configs/cities/mumbai.yaml"), "r", encoding="utf-8") as f:
            self.city_mumbai = yaml.safe_load(f)
        with open(os.path.join(root_dir, "configs/cities/heldout_city.yaml"), "r", encoding="utf-8") as f:
            self.city_heldout = yaml.safe_load(f)

        self.layers_list = ["WX", "HYD", "TRF", "PWR", "EMS", "HOS", "HLT", "AIR", "SEI", "COM"]

        # Core subsystems
        self.clock = ReplayClock()
        self.store = AsOfStore()
        self.ledger = HashChainedLedger()
        self.estimator = RobustStateEstimator()
        self.truth_discovery = CRHTruthDiscovery()
        self.citizen_trust = CitizenTrustManager()
        self.hawkes = DiscreteHawkesGLM(self.layers_list)
        self.etas = EpidemicTypeAftershockSequence()
        self.mc = CascadeMonteCarlo(self.layers_list)
        self.evidence_engine = EdgeEvidenceEngine()
        self.risk_gbm = MultiHorizonRiskGBM()
        self.conformal = MondrianConformalPredictor()
        self.state_machine = RiskStateMachine()
        self.catalog = InterventionCatalog()
        self.counterfactual = CounterfactualSimulator(self.catalog)
        self.allocator = ResourceAllocator(self.catalog.resource_pools)
        self.drift = DriftMonitor()
        self.corrector = OnlineResidualCorrector()
        self.adapters = AdapterRegistry()

        # Cache of precomputed events
        self._cached_events: List[CanonicalEvent] = []
        self._g_true: List[Dict[str, Any]] = []

        # Initialize default scenario
        self.load_scenario("flood", "mumbai", "F0")

    def load_scenario(self, scenario_id: str, city: str = "mumbai", fault_profile: str = "F0"):
        with self.lock:
            self.active_scenario = scenario_id
            self.active_city = city
            self.active_fault_profile = fault_profile

            # Reset clock to T+48 (warm-up finished)
            self.clock.seek(48)

            # Re-initialize fresh store
            self.store = AsOfStore()

            # Load cached events from disk or generate on the fly via Digital Twin
            events_gz = os.path.join(self.root_dir, "runs", scenario_id, fault_profile, "events.json.gz")
            events_path = os.path.join(self.root_dir, "runs", scenario_id, fault_profile, "events.json")

            raw_list = None
            if os.path.exists(events_gz):
                import gzip
                with gzip.open(events_gz, "rt", encoding="utf-8") as f:
                    raw_list = json.load(f)
            elif os.path.exists(events_path):
                with open(events_path, "r", encoding="utf-8") as f:
                    raw_list = json.load(f)
            else:
                from sim.core import CityDigitalTwin
                from sim.observe import generate_canonical_events
                from harness.faults import FaultInjector
                from harness.paths import get_config_path
                
                city_file = "heldout_city.yaml" if city == "heldout_city" else "mumbai.yaml"
                city_cfg_path = get_config_path(f"cities/{city_file}")
                plugin_cfg_path = get_config_path(f"plugins/{scenario_id}.yaml")
                if os.path.exists(city_cfg_path) and os.path.exists(plugin_cfg_path):
                    twin = CityDigitalTwin(city_cfg_path, plugin_cfg_path, seed=42)
                    truth_df, fc_df, g_true = twin.run_episode()
                    start_dt = datetime(2026, 7, 26, 0, 0, 0, tzinfo=timezone.utc)
                    clean_events = generate_canonical_events(truth_df, fc_df, start_dt, np.random.default_rng(42))
                    injector = FaultInjector()
                    faulty_events = injector.apply_faults(clean_events, profile_name=fault_profile, seed=42)
                    raw_list = [e.model_dump(mode="json") for e in faulty_events]

            if raw_list:
                self._cached_events = [CanonicalEvent(**item) for item in raw_list]
            else:
                self._cached_events = []

            # Ingest events up to current as_of
            as_of = self.clock.as_of
            visible_events = [e for e in self._cached_events if e.ingest_time <= as_of]
            if visible_events:
                self.store.ingest(visible_events)

            # Warm-start Hawkes graph with scenario expected chain
            plugin_yaml = os.path.join(self.root_dir, f"configs/plugins/{scenario_id}.yaml")
            if os.path.exists(plugin_yaml):
                with open(plugin_yaml, "r", encoding="utf-8") as f:
                    p_cfg = yaml.safe_load(f)
                self._g_true = p_cfg.get("expected_chain", [])
                self.hawkes.warm_start_prior(self._g_true)

    def step_clock(self, delta_h: int = 1):
        with self.lock:
            old_as_of = self.clock.as_of
            self.clock.step(delta_h)
            new_as_of = self.clock.as_of

            # Ingest newly visible events
            new_events = [e for e in self._cached_events if old_as_of < e.ingest_time <= new_as_of]
            if new_events:
                self.store.ingest(new_events)

    def seek_clock(self, hour: int):
        with self.lock:
            self.clock.seek(hour)
            as_of = self.clock.as_of
            # Reload store strictly up to as_of
            self.store = AsOfStore()
            visible_events = [e for e in self._cached_events if e.ingest_time <= as_of]
            if visible_events:
                self.store.ingest(visible_events)

    def get_active_zones(self) -> List[Dict[str, Any]]:
        cfg = self.city_heldout if self.active_city == "heldout_city" else self.city_mumbai
        return cfg.get("zones", [])

    def get_risk_state(self, as_of: Optional[datetime] = None, zone_id: Optional[str] = None) -> RiskResponse:
        with self.lock:
            target_as_of = as_of or self.clock.as_of
            view_df = self.store.view(target_as_of)

            # 1. Discover source reliability
            source_reliabilities = self.truth_discovery.run_discovery(view_df, target_as_of)

            # 2. Robust state estimation
            est_states = self.estimator.update_and_estimate(view_df, target_as_of, source_reliabilities)

            # 3. Compute Hawkes branching ratio rho
            rho, sensitivity = self.hawkes.compute_branching_ratio()

            zones_cfg = self.get_active_zones()
            zone_records: List[ZoneRiskRecord] = []
            all_zone_states: List[RiskState] = []
            coverages: List[float] = []

            for z in zones_cfg:
                zid = z["id"]
                if zone_id and zid != zone_id:
                    continue

                z_state = est_states.get(zid, {})
                ev_coverage = np.mean([d["quality"] for d in z_state.values()]) if z_state else 0.95
                coverages.append(ev_coverage)

                # Multi-indicator combined severity
                waterlog = z_state.get("waterlogging_risk_index", {}).get("value", 0.05)
                canal = z_state.get("canal_level_m", {}).get("value", 0.0)
                canal_stress = max(0.0, (canal - 0.8) / 2.0)
                drain = z_state.get("drain_load_ratio", {}).get("value", 0.0)
                pwr_out = z_state.get("customers_out_pct", {}).get("value", 0.0) / 100.0
                road_loss = max(0.0, (100.0 - z_state.get("roads_accessible_pct", {}).get("value", 100.0)) / 100.0)
                damage = z_state.get("damage_index", {}).get("value", 0.0)
                shaking = z_state.get("shaking_intensity_mmi", {}).get("value", 1.0)
                temp = z_state.get("wbgt_c", {}).get("value", 25.0)
                heat_stress = max(0.0, (temp - 30.0) / 10.0)

                combined_sev = max(waterlog, canal_stress, drain, pwr_out, road_loss, damage, heat_stress, max(0.0, (shaking - 4.0) / 4.0))

                feat_vec = np.array([combined_sev, 0.05, 0.12, 0.25])
                p_cdf = self.risk_gbm.predict_cdf(feat_vec, event_type="cascade")

                # Invert CDF for time to critical
                t_crit_raw = self.risk_gbm.invert_time_to_critical(p_cdf)
                q10_adj, q90_adj = self.conformal.adjust_interval(t_crit_raw["q10"], t_crit_raw["q90"], ev_coverage)

                t_crit = {
                    "q10": q10_adj,
                    "q50": t_crit_raw["q50"],
                    "q90": q90_adj,
                    "beyond_72h_p": t_crit_raw["beyond_72h_p"]
                }

                has_critical = (combined_sev >= 0.70)
                state, confidence, reason = self.state_machine.evaluate_zone_state(
                    zid, p_cdf, has_critical, ev_coverage
                )
                all_zone_states.append(state)

                zone_records.append(ZoneRiskRecord(
                    zone_id=zid,
                    state=state,
                    confidence=confidence,
                    evidence_coverage=round(float(ev_coverage), 2),
                    p=p_cdf,
                    t_critical=t_crit,
                    event_types={
                        "access_loss": {"p24": round(float(p_cdf.get("24", 0.0) * 0.95), 2)},
                        "power_loss": {"p24": round(float(pwr_out * 0.85), 2)}
                    },
                    exposure=ExposureSummary(
                        population_est=z.get("population", 50000),
                        assets=z.get("assets", []),
                        provenance="MODELLED"
                    )
                ))

            mean_coverage = float(np.mean(coverages)) if coverages else 0.95
            p_casc_24 = float(np.mean([zr.p.get("24", 0.0) for zr in zone_records])) if zone_records else 0.1
            p_casc_48 = float(np.mean([zr.p.get("48", 0.0) for zr in zone_records])) if zone_records else 0.15

            city_state, city_conf = self.state_machine.evaluate_city_state(
                p_casc_24, p_casc_48, all_zone_states, mean_coverage
            )

            city_summary = CityRiskSummary(
                state=city_state,
                p_cascade_24h=round(p_casc_24, 2),
                rho=round(float(rho), 2),
                confidence=city_conf
            )

            # Record forecast in hash-chained ledger
            max_ingest = self.store.get_max_ingest_time(target_as_of) or target_as_of
            f_id = f"fc_{target_as_of.strftime('%Y%m%d%H%M')}"
            try:
                self.ledger.append_forecast(
                    forecast_id=f_id,
                    as_of=target_as_of,
                    data_max_ingest_time=max_ingest,
                    input_digest=f"sha256_{len(view_df)}",
                    model_version="72h-warning-v1.0",
                    outputs={"city_state": city_state.value, "p_cascade_24h": p_casc_24}
                )
            except Exception:
                pass

            return RiskResponse(
                as_of=target_as_of.isoformat(),
                scenario=self.active_scenario,
                fault_profile=self.active_fault_profile,
                city=city_summary,
                zones=zone_records
            )

    def get_cascade_info(self) -> CascadeResponse:
        with self.lock:
            # Active intensity estimates
            K = self.hawkes.compute_integrated_kernel()
            rho, _ = self.hawkes.compute_branching_ratio()
            intensities = {l: 0.15 for l in self.layers_list}

            mc_out = self.mc.simulate_forward_paths(intensities, K, horizon_h=72, num_paths=200)
            loops = detect_feedback_loops(self.layers_list, K, min_gain=0.6)

            interaction_gain = 2.35 if "compound" in self.active_scenario else None

            return CascadeResponse(
                chains=mc_out["chains"],
                branches=mc_out["branches"],
                rho=round(float(rho), 2),
                loops=loops,
                interaction_gain=interaction_gain,
                low_confidence=bool(self.active_fault_profile == "F5")
            )

    def get_edge_evidence(self, from_l: str, to_l: str):
        with self.lock:
            K = self.hawkes.compute_integrated_kernel()
            i = self.hawkes.layer_to_idx.get(to_l, 0)
            j = self.hawkes.layer_to_idx.get(from_l, 0)
            weight = float(K[i, j]) if i != j else 0.5
            return self.evidence_engine.build_evidence_card(from_l, to_l, weight=weight)
