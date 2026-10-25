from __future__ import annotations
import os
import yaml
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from sim.layers.wx import simulate_wx, generate_weather_forecast
from sim.layers.hyd import HydrologySimulator
from sim.layers.trf import TrafficSimulator
from sim.layers.pwr import PowerGridSimulator
from sim.layers.ems import EMSSimulator
from sim.layers.hos import HospitalSimulator
from sim.layers.hlt import HealthSurveillanceSimulator
from sim.layers.air import AirPlumeSimulator
from sim.layers.sei import SeismicSimulator
from sim.layers.com import CommsSimulator

class CityDigitalTwin:
    """
    Mechanistic City Digital Twin simulating all 10 infrastructure layers.
    Coupling structure is hidden from the ML model to prevent inverse-crime bias.
    """
    def __init__(self, city_yaml_path: str, plugin_yaml_path: str, seed: int = 42):
        with open(city_yaml_path, "r", encoding="utf-8") as f:
            self.city_cfg = yaml.safe_load(f)
        with open(plugin_yaml_path, "r", encoding="utf-8") as f:
            self.plugin_cfg = yaml.safe_load(f)

        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.zones = self.city_cfg.get("zones", [])
        self.total_hours = 240

        # Instantiate layer simulators
        self.hyd_sim = HydrologySimulator(self.zones)
        self.trf_sim = TrafficSimulator(self.zones)
        self.pwr_sim = PowerGridSimulator(self.zones)
        self.ems_sim = EMSSimulator(self.zones)
        self.hos_sim = HospitalSimulator(self.zones)
        self.hlt_sim = HealthSurveillanceSimulator(self.zones)
        self.air_sim = AirPlumeSimulator(self.zones)
        self.sei_sim = SeismicSimulator(self.zones)
        self.com_sim = CommsSimulator(self.zones)

    def run_episode(
        self,
        interventions_active: Optional[List[str]] = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame, List[Dict[str, Any]]]:
        """
        Executes a 240-hour simulation run.
        Returns:
          1. truth_df: physical state per (hour, zone, layer, variable, value)
          2. forecasts_df: issued weather forecasts at each 6-hour cycle with error growth
          3. g_true: ground truth causal coupling edges for scoring dependency recovery
        """
        interventions = interventions_active or []
        records = []
        forecast_records = []

        # Weather lookup closure
        def get_wx(t):
            sub_rng = np.random.default_rng(self.seed + t)
            return simulate_wx(t, self.plugin_cfg, sub_rng)

        for t in range(self.total_hours):
            wx = get_wx(t)
            # Record WX state for each zone
            for z in self.zones:
                zid = z["id"]
                for k, v in wx.items():
                    records.append({
                        "hour": t, "zone_id": zid, "layer": "WX", "variable": k, "value": v
                    })

            # Issue weather forecasts every 6 hours
            if t % 6 == 0:
                for lead in [1, 3, 6, 12, 24, 48, 72]:
                    if t + lead < self.total_hours:
                        fc_wx = generate_weather_forecast(t, lead, get_wx, self.rng)
                        for z in self.zones:
                            for k, v in fc_wx.items():
                                forecast_records.append({
                                    "issued_hour": t,
                                    "valid_hour": t + lead,
                                    "lead_h": lead,
                                    "zone_id": z["id"],
                                    "layer": "WX",
                                    "variable": k,
                                    "forecast_value": v
                                })

            # Step other layers
            hyd = self.hyd_sim.step(wx["rain_mm_h"], interventions, self.rng)
            sei = self.sei_sim.step(t, self.plugin_cfg, self.rng)
            air = self.air_sim.step(t, self.plugin_cfg, wx["wind_speed_mps"], wx["wind_dir_deg"], interventions, self.rng)
            pwr = self.pwr_sim.step(t, wx["temp_c"], hyd, sei, interventions, self.rng)
            trf = self.trf_sim.step(t, hyd, pwr, sei, air, interventions)
            ems = self.ems_sim.step(t, wx, trf, hyd, sei, interventions, self.rng)
            hlt = self.hlt_sim.step(t, self.plugin_cfg, self.rng)
            hos = self.hos_sim.step(t, ems, hlt, pwr, air, interventions, self.rng)
            com = self.com_sim.step(t, ems, pwr, hyd, sei, self.rng)

            # Accumulate layer outputs
            for zid in [z["id"] for z in self.zones]:
                for k, v in hyd.get(zid, {}).items():
                    records.append({"hour": t, "zone_id": zid, "layer": "HYD", "variable": k, "value": v})
                for k, v in sei.get(zid, {}).items():
                    records.append({"hour": t, "zone_id": zid, "layer": "SEI", "variable": k, "value": v})
                for k, v in air.get(zid, {}).items():
                    records.append({"hour": t, "zone_id": zid, "layer": "AIR", "variable": k, "value": v})
                for k, v in pwr.get(zid, {}).items():
                    records.append({"hour": t, "zone_id": zid, "layer": "PWR", "variable": k, "value": v})
                for k, v in trf.get(zid, {}).items():
                    records.append({"hour": t, "zone_id": zid, "layer": "TRF", "variable": k, "value": v})
                for k, v in ems.get(zid, {}).items():
                    records.append({"hour": t, "zone_id": zid, "layer": "EMS", "variable": k, "value": v})
                for k, v in hlt.get(zid, {}).items():
                    records.append({"hour": t, "zone_id": zid, "layer": "HLT", "variable": k, "value": v})
                for k, v in hos.get(zid, {}).items():
                    records.append({"hour": t, "zone_id": zid, "layer": "HOS", "variable": k, "value": v})
                for k, v in com.get(zid, {}).items():
                    records.append({"hour": t, "zone_id": zid, "layer": "COM", "variable": k, "value": v})

        truth_df = pd.DataFrame(records)
        forecasts_df = pd.DataFrame(forecast_records)
        g_true = self.plugin_cfg.get("expected_chain", [])

        return truth_df, forecasts_df, g_true
