from __future__ import annotations
import math
import numpy as np
from typing import Dict, Any, List

class TrafficSimulator:
    """
    Traffic network velocity and accessibility simulator.
    Degrades speed and road connectivity based on waterlogging, seismic damage, plume cordons, and power loss.
    """
    def __init__(self, zones: List[Dict[str, Any]]):
        self.zones = [z["id"] for z in zones]

    def step(
        self,
        t_h: int,
        hyd_states: Dict[str, Dict[str, float]],
        pwr_states: Dict[str, Dict[str, float]],
        sei_states: Dict[str, Dict[str, float]],
        air_states: Dict[str, Dict[str, float]],
        interventions_active: List[str]
    ) -> Dict[str, Dict[str, float]]:
        outputs = {}
        # Rush hour diurnal demand curve
        diurnal_demand = 0.75 + 0.25 * math.sin((t_h - 8) * 2 * math.pi / 24.0)

        for zid in self.zones:
            waterlogging = hyd_states.get(zid, {}).get("waterlogging_risk_index", 0.0)
            pwr_out = pwr_states.get(zid, {}).get("customers_out_pct", 0.0) / 100.0
            damage = sei_states.get(zid, {}).get("damage_index", 0.0)
            gas_conc = air_states.get(zid, {}).get("concentration_index", 0.0)

            # Signal outage degradation factor
            signal_factor = 1.0 - 0.35 * pwr_out

            # Waterlogging blockage (sigmoidal severance)
            water_factor = max(0.05, 1.0 - 0.85 / (1.0 + np.exp(-6.0 * (waterlogging - 0.45))))

            # Seismic debris blockage
            quake_factor = max(0.10, 1.0 - 0.90 * damage)

            # Chemical plume exclusion cordon
            plume_factor = 0.25 if gas_conc >= 2.5 else 1.0

            # Side effects from interventions
            if "low_lying_evacuation" in interventions_active:
                evac_penalty = 0.65 # arterial congestion
            else:
                evac_penalty = 1.0

            speed_idx = float(
                np.clip(
                    0.88 * diurnal_demand * signal_factor * water_factor * quake_factor * plume_factor * evac_penalty,
                    0.05,
                    1.0
                )
            )

            # Roads accessible percentage
            accessible_pct = float(
                np.clip(
                    100.0 * min(water_factor, quake_factor, plume_factor) * (0.8 + 0.2 * signal_factor),
                    5.0,
                    100.0
                )
            )

            outputs[zid] = {
                "speed_index": speed_idx,
                "roads_accessible_pct": accessible_pct
            }

        return outputs
