from __future__ import annotations
import numpy as np
from typing import Dict, Any, List

class CommsSimulator:
    """
    Telecommunications network traffic and citizen report generation simulator.
    Fails when power outages exceed cell tower battery reserves.
    """
    def __init__(self, zones: List[Dict[str, Any]]):
        self.zones = [z["id"] for z in zones]

    def step(
        self,
        t_h: int,
        ems_states: Dict[str, Dict[str, float]],
        pwr_states: Dict[str, Dict[str, float]],
        hyd_states: Dict[str, Dict[str, float]],
        sei_states: Dict[str, Dict[str, float]],
        rng: np.random.Generator
    ) -> Dict[str, Dict[str, float]]:
        outputs = {}

        for zid in self.zones:
            pwr_out = pwr_states.get(zid, {}).get("customers_out_pct", 0.0)
            ems_calls = ems_states.get(zid, {}).get("call_rate_per_k", 1.2)
            waterlogging = hyd_states.get(zid, {}).get("waterlogging_risk_index", 0.0)
            shaking = sei_states.get(zid, {}).get("shaking_intensity_mmi", 1.0)

            # High power outage drains battery backup over time
            if pwr_out >= 70.0:
                net_load = 98.0 + rng.normal(0, 3.0)
            else:
                net_load = 40.0 + 8.0 * ems_calls + rng.normal(0, 2.0)

            # Citizen reports: rate correlates with visible disruption
            visible_severity = max(waterlogging * 1.5, max(0.0, shaking - 4.0))
            base_reports = 3.0 + 25.0 * visible_severity + rng.normal(0, 1.5)

            outputs[zid] = {
                "network_load_pct": float(np.clip(net_load, 5.0, 150.0)),
                "citizen_reports_rate": float(np.clip(base_reports, 0.0, 500.0))
            }

        return outputs
