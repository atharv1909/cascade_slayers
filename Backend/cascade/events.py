from __future__ import annotations
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
import yaml

class EventExtractor:
    """
    Extracts discrete onset events (severity >= 2 degraded, = 3 failed)
    across the 10 urban layers per zone to construct the event tensor N[t, zone, type].
    """
    def __init__(self, thresholds_yaml: Optional[str] = None):
        from harness.paths import get_config_path
        if thresholds_yaml is None:
            thresholds_yaml = get_config_path("thresholds.yaml")
        with open(thresholds_yaml, "r", encoding="utf-8") as f:
            self.ladders = yaml.safe_load(f)["severity_ladder"]

        self.event_types = [
            "access_loss",
            "power_loss",
            "hospital_saturation",
            "heat_stress",
            "contamination_exposure",
            "structural_damage",
            "comms_loss"
        ]

    def compute_severity(self, layer: str, var: str, value: float) -> int:
        """Returns severity level: 0 (normal), 1 (stressed), 2 (degraded), 3 (failed)."""
        ladder = self.ladders.get(layer, {}).get(var)
        if not ladder:
            return 0

        # Handle inverse variables where lower values mean higher severity
        if var in ["speed_index", "roads_accessible_pct", "generator_hours_rem"]:
            if value <= ladder["failed"]:
                return 3
            elif value <= ladder["degraded"]:
                return 2
            elif value <= ladder["stressed"]:
                return 1
            return 0
        else:
            if value >= ladder["failed"]:
                return 3
            elif value >= ladder["degraded"]:
                return 2
            elif value >= ladder["stressed"]:
                return 1
            return 0

    def extract_discrete_events(
        self,
        estimated_states: Dict[str, Dict[str, Dict[str, float]]]
    ) -> List[Dict[str, Any]]:
        """
        Extracts active degraded/failed events across all zones.
        Returns: [ { "zone_id": z, "layer": l, "event_type": ev, "severity": s, "value": v } ]
        """
        active_events = []

        var_to_event = {
            "waterlogging_risk_index": ("HYD", "waterlogging_drain_overload"),
            "speed_index": ("TRF", "access_loss"),
            "roads_accessible_pct": ("TRF", "arterial_access_loss"),
            "customers_out_pct": ("PWR", "power_loss"),
            "icu_occupancy_pct": ("HOS", "hospital_saturation"),
            "wbgt_c": ("WX", "heat_stress"),
            "concentration_index": ("AIR", "contamination_exposure"),
            "damage_index": ("SEI", "structural_damage"),
            "network_load_pct": ("COM", "comms_loss")
        }

        for zid, vars_dict in estimated_states.items():
            for var_name, data in vars_dict.items():
                val = data["value"]
                if var_name in var_to_event:
                    layer, ev_type = var_to_event[var_name]
                    sev = self.compute_severity(layer, var_name, val)
                    if sev >= 2:
                        active_events.append({
                            "zone_id": zid,
                            "layer": layer,
                            "event_type": ev_type,
                            "severity": sev,
                            "value": val
                        })

        return active_events
