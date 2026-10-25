from __future__ import annotations
import numpy as np
from typing import Dict, Any, List

class HydrologySimulator:
    """
    SCS Curve Number runoff with reservoir retention and elevation-based downhill routing.
    Not a Hawkes process; uses physical saturation, storage, and hydraulic outflow.
    """
    def __init__(self, zones: List[Dict[str, Any]]):
        self.zones = {z["id"]: z for z in zones}
        self.storage = {z["id"]: 0.0 for z in zones}
        self.curve_number = {z["id"]: 88.0 for z in zones} # Urban impervious

    def step(
        self,
        rain_mm_h: float,
        interventions_active: List[str],
        rng: np.random.Generator
    ) -> Dict[str, Dict[str, float]]:
        outputs = {}
        inflows = {zid: 0.0 for zid in self.zones}

        # Step 1: Compute local runoff via SCS Curve Number
        for zid, z in self.zones.items():
            cn = self.curve_number[zid]
            s_potential = (25400.0 / cn) - 254.0 # Potential max retention in mm
            ia = 0.2 * s_potential               # Initial abstraction

            if rain_mm_h > ia:
                direct_runoff = ((rain_mm_h - ia) ** 2) / (rain_mm_h - ia + s_potential)
            else:
                direct_runoff = 0.0

            inflows[zid] += direct_runoff

        # Step 2: Storage routing and downstream spillover
        pump_mult = 1.65 if "preposition_pumps" in interventions_active else 1.0

        for zid, z in self.zones.items():
            elevation = z.get("elevation_m", 5.0)
            # Low elevation zones have higher drainage resistance
            base_capacity = max(15.0, 10.0 + elevation * 4.0) * pump_mult
            
            # Update storage with inflow
            self.storage[zid] = max(0.0, self.storage[zid] * 0.70 + inflows[zid])
            
            drain_ratio = self.storage[zid] / base_capacity
            overflow = max(0.0, self.storage[zid] - base_capacity)

            # Route overflow downhill
            downstream = z.get("downstream_zones", [])
            if downstream and overflow > 0:
                share = overflow / len(downstream)
                for d_id in downstream:
                    if d_id in inflows:
                        inflows[d_id] += share

            canal_level_m = 1.2 + 3.5 * min(1.5, drain_ratio)
            # Waterlogging risk index: sigmoid on overflow depth
            waterlogging_risk = float(1.0 / (1.0 + np.exp(-3.5 * (drain_ratio - 0.9))))

            outputs[zid] = {
                "drain_load_ratio": float(np.clip(drain_ratio, 0.0, 3.0)),
                "canal_level_m": float(np.clip(canal_level_m, 0.5, 8.0)),
                "waterlogging_risk_index": float(np.clip(waterlogging_risk, 0.0, 1.0))
            }

        return outputs
