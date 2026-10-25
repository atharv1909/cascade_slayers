from __future__ import annotations
import math
import numpy as np
from typing import Dict, Any, List

class PowerGridSimulator:
    """
    Simulates power grid demand, thermal loading, flood-induced tripping, and cascading feeder failures.
    """
    def __init__(self, zones: List[Dict[str, Any]]):
        self.zones = [z["id"] for z in zones]
        self.feeder_status = {zid: 1.0 for zid in self.zones} # 1.0 = healthy, 0.0 = tripped
        self.trip_timer = {zid: 0 for zid in self.zones}

    def step(
        self,
        t_h: int,
        temp_c: float,
        hyd_states: Dict[str, Dict[str, float]],
        sei_states: Dict[str, Dict[str, float]],
        interventions_active: List[str],
        rng: np.random.Generator
    ) -> Dict[str, Dict[str, float]]:
        outputs = {}
        # Diurnal electricity demand
        diurnal = 0.80 + 0.20 * math.sin((t_h - 14) * 2 * math.pi / 24.0)

        # Thermal air conditioning sensitivity beta: +3.5% load per degree above 28 C
        thermal_excess = max(0.0, temp_c - 28.0)
        thermal_mult = 1.0 + 0.035 * thermal_excess

        if "rolling_load_shed" in interventions_active:
            shed_reduction = 0.85
        else:
            shed_reduction = 1.0

        for zid in self.zones:
            waterlogging = hyd_states.get(zid, {}).get("waterlogging_risk_index", 0.0)
            shaking = sei_states.get(zid, {}).get("shaking_intensity_mmi", 1.0)

            # Substation flood hazard trip
            if waterlogging > 0.65 and self.feeder_status[zid] == 1.0:
                if rng.random() < 0.35:
                    self.feeder_status[zid] = 0.0
                    self.trip_timer[zid] = rng.integers(8, 24)

            # Seismic tripping
            if shaking >= 6.5 and self.feeder_status[zid] == 1.0:
                if rng.random() < 0.60:
                    self.feeder_status[zid] = 0.0
                    self.trip_timer[zid] = rng.integers(12, 48)

            # Restoration countdown
            if self.feeder_status[zid] == 0.0:
                self.trip_timer[zid] -= 1
                if self.trip_timer[zid] <= 0:
                    self.feeder_status[zid] = 1.0

            raw_load_ratio = 0.55 * diurnal * thermal_mult * shed_reduction
            substation_loading_pct = 65.0 * diurnal * thermal_mult * shed_reduction

            # If tripped, customers out rises
            if self.feeder_status[zid] == 0.0:
                customers_out = float(rng.uniform(70.0, 98.0))
                substation_loading_pct = 0.0
            else:
                customers_out = float(max(0.5, rng.normal(1.2, 0.4)))

            outputs[zid] = {
                "load_ratio": float(np.clip(raw_load_ratio, 0.1, 2.5)),
                "substation_loading": float(np.clip(substation_loading_pct, 0.0, 180.0)),
                "customers_out_pct": float(np.clip(customers_out, 0.0, 100.0))
            }

        return outputs
