from __future__ import annotations
import math
import numpy as np
from typing import Dict, Any, List

class EMSSimulator:
    """
    Simulates emergency dispatch call volume, fleet M/M/c queuing delays, and response times.
    """
    def __init__(self, zones: List[Dict[str, Any]]):
        self.zones = [z["id"] for z in zones]

    def step(
        self,
        t_h: int,
        wx_states: Dict[str, float],
        trf_states: Dict[str, Dict[str, float]],
        hyd_states: Dict[str, Dict[str, float]],
        sei_states: Dict[str, Dict[str, float]],
        interventions_active: List[str],
        rng: np.random.Generator
    ) -> Dict[str, Dict[str, float]]:
        outputs = {}
        rain = wx_states.get("rain_mm_h", 0.0)
        wbgt = wx_states.get("wbgt_c", 25.0)

        # Baseline call rate multipliers
        weather_mult = 1.0 + 0.015 * rain
        heat_mult = 1.0 + 0.08 * max(0.0, wbgt - 30.0)

        staged_bonus = 0.70 if "stage_ambulances" in interventions_active else 1.0

        for zid in self.zones:
            speed = trf_states.get(zid, {}).get("speed_index", 0.8)
            waterlogging = hyd_states.get(zid, {}).get("waterlogging_risk_index", 0.0)
            shaking = sei_states.get(zid, {}).get("shaking_intensity_mmi", 1.0)

            incident_mult = 1.0 + 1.8 * waterlogging + 2.5 * max(0.0, shaking - 4.5)
            call_rate = 1.2 * weather_mult * heat_mult * incident_mult + rng.normal(0, 0.15)
            call_rate = max(0.2, call_rate)

            # M/M/c queue and road transit delay
            # base transit 9 min / speed_idx + queue backlog
            base_transit = 9.0 / max(0.15, speed) * staged_bonus
            queue_delay = max(0.0, (call_rate - 1.5) * 6.5)

            response_time = float(np.clip(base_transit + queue_delay + rng.normal(0, 1.2), 5.0, 120.0))
            unavailable_pct = float(np.clip((call_rate / 4.0) * 80.0, 5.0, 95.0))

            outputs[zid] = {
                "call_rate_per_k": float(np.clip(call_rate, 0.1, 50.0)),
                "response_time_min": response_time,
                "units_unavailable_pct": unavailable_pct
            }

        return outputs
