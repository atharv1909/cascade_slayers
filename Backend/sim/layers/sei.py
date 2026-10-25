from __future__ import annotations
import math
import numpy as np
from typing import Dict, Any, List

class SeismicSimulator:
    """
    Simulates mainshock shaking via Ground Motion Prediction Equation (GMPE),
    structural fragility lognormal damage, and ETAS aftershock rates.
    """
    def __init__(self, zones: List[Dict[str, Any]]):
        self.zones = {z["id"]: z for z in zones}

    def step(
        self,
        t_h: int,
        scenario_cfg: Dict[str, Any],
        rng: np.random.Generator
    ) -> Dict[str, Dict[str, float]]:
        outputs = {}
        scenario_id = scenario_cfg.get("id", "")
        trig = scenario_cfg.get("trigger_generator", {})
        onset_h = trig.get("onset_hour", 50)
        is_seismic_scenario = (scenario_id in ["quake", "compound_b"]) and (t_h >= onset_h)

        mag = trig.get("magnitude_mw", 6.4)
        epi_lat = trig.get("epicenter_lat", 19.062)
        epi_lon = trig.get("epicenter_lon", 72.871)

        for zid, z in self.zones.items():
            if not is_seismic_scenario:
                outputs[zid] = {
                    "shaking_intensity_mmi": 1.0,
                    "aftershock_rate_per_h": 0.0,
                    "damage_index": 0.0
                }
            else:
                elapsed_h = t_h - onset_h
                # Hypocentral distance in km (assuming depth = 12 km)
                d_lat = (z["lat"] - epi_lat) * 111.0
                d_lon = (z["lon"] - epi_lon) * 111.0 * math.cos(math.radians(epi_lat))
                r_hypo = math.sqrt(d_lat**2 + d_lon**2 + 12.0**2)

                # GMPE (Atkinson-Boore style log PGA to MMI)
                # MMI = c1 + c2*M - c3*log10(R)
                base_mmi = 1.15 + 1.25 * mag - 2.8 * math.log10(max(10.0, r_hypo))
                mmi = max(1.0, base_mmi + rng.normal(0, 0.2))

                # Lognormal fragility curve for structural damage index
                # Fragility median theta = MMI 6.8, beta = 0.35
                damage = float(1.0 / (1.0 + np.exp(-1.8 * (mmi - 6.5))))

                # ETAS Omori law aftershock rate: lambda(t) = K / (t + c)^p
                # K = 15.0, c = 0.5, p = 1.05
                aftershock_rate = float(15.0 / ((elapsed_h + 0.5) ** 1.05)) if elapsed_h >= 0 else 0.0

                outputs[zid] = {
                    "shaking_intensity_mmi": float(np.clip(mmi, 1.0, 12.0)),
                    "aftershock_rate_per_h": float(np.clip(aftershock_rate, 0.0, 50.0)),
                    "damage_index": float(np.clip(damage, 0.0, 1.0))
                }

        return outputs
