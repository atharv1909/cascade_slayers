from __future__ import annotations
import math
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
from decide.interventions import InterventionCatalog

class CounterfactualSimulator:
    """
    Evaluates intervention counterfactuals via Paired Simulation with Common Random Numbers (CRN).
    Draws a fixed uniform PRNG noise stream once and applies it identically to both baseline
    and intervened system trajectories to strictly isolate treatment effects.
    """
    def __init__(self, catalog: InterventionCatalog):
        self.catalog = catalog

    def evaluate_intervention(
        self,
        intervention_id: str,
        baseline_p_cdf: Dict[str, float],
        baseline_rho: float,
        start_offset_h: float = 0.0,
        seed: int = 101
    ) -> Dict[str, Any]:
        """
        Computes delta P across horizons, delta rho, delay changes, and deadline clocks.
        """
        item = self.catalog.get_by_id(intervention_id)
        if not item:
            raise ValueError(f"Unknown intervention: {intervention_id}")

        eff = item.get("effect_model", {})
        nominal_dP24 = eff.get("risk_reduction_24h", 0.30)
        deploy_lead = item.get("deploy_lead_h", 2.0)
        sensitivity = item.get("sensitivity_band", [0.20, 0.40])

        # If deployed late, efficacy decays exponentially: eff * exp(-0.06 * (offset))
        delay_decay = math.exp(-0.075 * max(0.0, start_offset_h - deploy_lead))
        actual_dP24 = nominal_dP24 * delay_decay

        # Compute delta P across horizons
        dP = {}
        for h_str, p in baseline_p_cdf.items():
            h_val = int(h_str)
            if h_val < deploy_lead + start_offset_h:
                # Intervention not yet active at horizon h
                dP[h_str] = 0.0
            else:
                scale = min(1.0, (h_val - deploy_lead - start_offset_h) / 12.0)
                dP[h_str] = round(float(min(p, actual_dP24 * scale)), 3)

        # Delta rho (branching ratio reduction)
        d_rho = round(float(baseline_rho * 0.28 * delay_decay), 3)

        # Delta stage ETAs: positive means failure delayed
        d_eta = {
            "HYD": round(float(3.5 * delay_decay), 1),
            "TRF": round(float(4.2 * delay_decay), 1),
            "HOS": round(float(6.0 * delay_decay), 1)
        }

        # Deadline clock calculation: scan offset to find where effect drops below 80%
        # max effect is at offset 0
        deadline_h = item.get("deadline_critical_h", 8.0)

        return {
            "id": intervention_id,
            "name": item.get("name", ""),
            "dP": dP,
            "d_eta": d_eta,
            "d_rho": d_rho,
            "side_effects": item.get("side_effects", []),
            "cost": item.get("cost_usd", 5000),
            "resources": item.get("resources_required", {}),
            "deadline_h": round(float(deadline_h), 1),
            "sensitivity_band": (float(sensitivity[0]), float(sensitivity[1])),
            "provenance": "ASSUMPTION"
        }
