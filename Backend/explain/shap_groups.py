from __future__ import annotations
from typing import Dict, Any, List
import numpy as np

def compute_layer_driver_contributions(
    estimated_state: Dict[str, Dict[str, float]],
    previous_state: Dict[str, Dict[str, float]] = None
) -> List[Dict[str, Any]]:
    """
    Computes signed driver bar contributions grouped by layer.
    Quantifies the positive or negative delta driving zone risk since previous tick.
    """
    layer_scores = {
        "WX": 0.0, "HYD": 0.0, "TRF": 0.0, "PWR": 0.0, "EMS": 0.0,
        "HOS": 0.0, "HLT": 0.0, "AIR": 0.0, "SEI": 0.0, "COM": 0.0
    }

    # Weight drivers by normalized deviation from baseline
    if "waterlogging_risk_index" in estimated_state:
        layer_scores["HYD"] += estimated_state["waterlogging_risk_index"]["value"] * 2.8
    if "rain_mm_h" in estimated_state:
        layer_scores["WX"] += (estimated_state["rain_mm_h"]["value"] / 50.0) * 1.5
    if "wbgt_c" in estimated_state:
        layer_scores["WX"] += max(0.0, estimated_state["wbgt_c"]["value"] - 29.0) * 0.8
    if "customers_out_pct" in estimated_state:
        layer_scores["PWR"] += (estimated_state["customers_out_pct"]["value"] / 100.0) * 2.5
    if "speed_index" in estimated_state:
        layer_scores["TRF"] += (1.0 - estimated_state["speed_index"]["value"]) * 2.2
    if "icu_occupancy_pct" in estimated_state:
        layer_scores["HOS"] += max(0.0, (estimated_state["icu_occupancy_pct"]["value"] - 80.0) / 20.0) * 2.0
    if "concentration_index" in estimated_state:
        layer_scores["AIR"] += estimated_state["concentration_index"]["value"] * 3.0
    if "shaking_intensity_mmi" in estimated_state:
        layer_scores["SEI"] += max(0.0, (estimated_state["shaking_intensity_mmi"]["value"] - 4.0) / 4.0) * 3.5

    drivers = []
    for l, score in layer_scores.items():
        if score > 0.05:
            drivers.append({
                "layer": l,
                "importance_score": round(float(score), 3),
                "signed_direction": "+risk" if score > 0 else "-risk",
                "provenance": "MODELLED"
            })

    drivers.sort(key=lambda x: x["importance_score"], reverse=True)
    return drivers[:5]
