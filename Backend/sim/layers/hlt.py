from __future__ import annotations
import math
import numpy as np
from typing import Dict, Any, List

class HealthSurveillanceSimulator:
    """
    Metapopulation SEIR transmission dynamic over urban mobility graph.
    ED syndromic indicators lead clinical PCR test counts by 3-5 days.
    """
    def __init__(self, zones: List[Dict[str, Any]]):
        self.zones = [z["id"] for z in zones]
        # SEIR compartments per zone
        self.S = {zid: 100000.0 for zid in self.zones}
        self.E = {zid: 20.0 for zid in self.zones}
        self.I = {zid: 5.0 for zid in self.zones}
        self.R = {zid: 0.0 for zid in self.zones}

    def step(
        self,
        t_h: int,
        scenario_cfg: Dict[str, Any],
        rng: np.random.Generator
    ) -> Dict[str, Dict[str, float]]:
        outputs = {}
        scenario_id = scenario_cfg.get("id", "")
        trig = scenario_cfg.get("trigger_generator", {})
        onset_h = trig.get("onset_hour", 48)
        r0 = trig.get("r0_initial", 1.05) if scenario_id == "epidemic" else 0.95

        is_epidemic_active = (scenario_id == "epidemic" and t_h >= onset_h)
        beta_trans = (r0 / (5.0 * 24.0)) if is_epidemic_active else (0.85 / (5.0 * 24.0))
        sigma_inc = 1.0 / (4.0 * 24.0)
        gamma_rec = 1.0 / (7.0 * 24.0)

        for zid in self.zones:
            s, e, i, r = self.S[zid], self.E[zid], self.I[zid], self.R[zid]
            total_pop = s + e + i + r

            new_inf = beta_trans * s * i / total_pop
            new_infectious = sigma_inc * e
            new_rec = gamma_rec * i

            self.S[zid] = max(0.0, s - new_inf)
            self.E[zid] = max(0.0, e + new_inf - new_infectious)
            self.I[zid] = max(0.0, i + new_infectious - new_rec)
            self.R[zid] = max(0.0, r + new_rec)

            # Syndromic ED presentations are a fraction of active infectious individuals
            syndromic_count = float(np.clip(0.12 * self.I[zid] + rng.normal(0, 1.5), 0.0, 500.0))
            
            # Instantaneous reproduction number Rt
            rt_val = float(np.clip(r0 * (self.S[zid] / total_pop) + rng.normal(0, 0.04), 0.4, 4.5))
            doubling_time = float(70.0 / max(0.01, (rt_val - 1.0) * 12.0)) if rt_val > 1.02 else 99.0

            outputs[zid] = {
                "ed_syndromic_count": syndromic_count,
                "rt": rt_val,
                "doubling_time_days": float(np.clip(doubling_time, 1.0, 100.0))
            }

        return outputs
