from __future__ import annotations
import math
import numpy as np
from typing import Dict, Any, List

class AirPlumeSimulator:
    """
    Gaussian puff dispersion model for hazardous toxic gas release.
    Calculates downwind concentration based on distance from release source and wind vector.
    """
    def __init__(self, zones: List[Dict[str, Any]]):
        self.zones = {z["id"]: z for z in zones}

    def step(
        self,
        t_h: int,
        scenario_cfg: Dict[str, Any],
        wind_speed_mps: float,
        wind_dir_deg: float,
        interventions_active: List[str],
        rng: np.random.Generator
    ) -> Dict[str, Dict[str, float]]:
        outputs = {}
        scenario_id = scenario_cfg.get("id", "")
        trig = scenario_cfg.get("trigger_generator", {})
        onset_h = trig.get("onset_hour", 54)
        is_release_scenario = (scenario_id in ["chem", "compound_b"]) and (t_h >= onset_h)

        source_zone = trig.get("source_zone", "z11_airside_mithi")
        source_coords = (
            self.zones[source_zone]["lat"],
            self.zones[source_zone]["lon"]
        ) if source_zone in self.zones else (19.088, 72.866)

        # Wind direction blowing towards (add 180 deg)
        downwind_deg = (wind_dir_deg + 180.0) % 360.0
        downwind_rad = math.radians(downwind_deg)

        # Valve isolation intervention breaks the leak release
        if "gas_isolation_valves" in interventions_active:
            release_strength = 0.15
        else:
            release_strength = 1.0

        for zid, z in self.zones.items():
            if not is_release_scenario or (t_h - onset_h) > 18:
                # Normal background AQI
                conc = 0.05 + rng.normal(0, 0.01)
                aqi = 85.0 + rng.normal(0, 5.0)
            else:
                elapsed_h = t_h - onset_h
                # Compute displacement vector in km
                d_lat = (z["lat"] - source_coords[0]) * 111.0
                d_lon = (z["lon"] - source_coords[1]) * 111.0 * math.cos(math.radians(source_coords[0]))
                dist_km = math.sqrt(d_lat**2 + d_lon**2)

                # Angle between source-to-zone and wind vector
                bearing = math.atan2(d_lon, d_lat)
                angle_diff = abs(bearing - downwind_rad)
                angle_diff = min(angle_diff, 2 * math.pi - angle_diff)

                # Puff travel distance
                travel_km = (wind_speed_mps * 3.6) * elapsed_h

                if dist_km <= travel_km + 1.5 and angle_diff < math.radians(45.0):
                    # Pasquill-Gifford dispersion approximation
                    sigma_y = max(0.2, 0.15 * dist_km)
                    crosswind_dist = dist_km * math.sin(angle_diff)
                    plume_factor = math.exp(-0.5 * (crosswind_dist / sigma_y) ** 2)
                    conc = release_strength * (6.5 / (1.0 + 0.8 * dist_km)) * plume_factor
                    aqi = 120.0 + conc * 75.0
                else:
                    conc = 0.05 + rng.normal(0, 0.01)
                    aqi = 85.0 + rng.normal(0, 5.0)

            outputs[zid] = {
                "concentration_index": float(np.clip(conc, 0.0, 15.0)),
                "aqi": float(np.clip(aqi, 20.0, 999.0))
            }

        return outputs
