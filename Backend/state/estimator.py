from __future__ import annotations
import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
import yaml

class RobustStateEstimator:
    """
    Robust State Estimator incorporating:
      - Hampel 3-sigma outlier filtering
      - Physical bounds enforcement
      - Reliability-weighted multi-source median fusion
      - Staleness-inflated Kalman-lite variance: sigma^2(t) = sigma^2_last + q * (t - t_last)
    """
    def __init__(self, variables_yaml: Optional[str] = None):
        from harness.paths import get_config_path
        if variables_yaml is None:
            variables_yaml = get_config_path("variables.yaml")
        with open(variables_yaml, "r", encoding="utf-8") as f:
            self.vars_cfg = yaml.safe_load(f)["layers"]
        
        # State tracking: (zone_id, variable) -> { 'x': float, 'var': float, 't_last': datetime }
        self._states: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._q_drift = 0.05  # variance inflation rate per hour of staleness

    def _get_bounds(self, layer: str, var: str) -> Tuple[float, float]:
        cfg = self.vars_cfg.get(layer, {}).get("variables", {}).get(var, {})
        return cfg.get("min", -1e6), cfg.get("physical_max", 1e6)

    def hampel_filter(self, values: List[float], k: int = 3) -> List[float]:
        """Simple median absolute deviation (MAD) Hampel filter."""
        if len(values) < 3:
            return values
        arr = np.array(values)
        med = np.median(arr)
        mad = np.median(np.abs(arr - med))
        threshold = k * 1.4826 * max(1e-4, mad)
        return [v if abs(v - med) <= threshold else float(med) for v in values]

    def update_and_estimate(
        self,
        events_df: pd.DataFrame,
        as_of: datetime,
        source_reliabilities: Optional[Dict[str, float]] = None
    ) -> Dict[str, Dict[str, Dict[str, float]]]:
        """
        Processes events visible up to as_of.
        Returns estimated state and variance per (zone_id, variable).
        Format: { zone_id: { variable: { "value": x, "variance": var, "staleness_h": st, "quality": q } } }
        """
        reliabilities = source_reliabilities or {}
        results: Dict[str, Dict[str, Dict[str, float]]] = {}

        if events_df.empty:
            return results

        # Group by zone and variable
        for (zid, layer, var), group in events_df.groupby(["zone_id", "layer", "variable"]):
            min_val, max_val = self._get_bounds(layer, var)
            raw_vals = [float(v) for v in group["value"].tolist()]
            # Apply Hampel filter
            cleaned_vals = self.hampel_filter(raw_vals)

            # Reliability weights
            weights = [reliabilities.get(s, 1.0) for s in group["source_id"].tolist()]
            weights = np.array(weights)
            if weights.sum() > 0:
                weights /= weights.sum()
            else:
                weights = np.ones(len(cleaned_vals)) / len(cleaned_vals)

            # Reliability-weighted consensus value
            fused_val = float(np.sum(np.array(cleaned_vals) * weights))
            fused_val = float(np.clip(fused_val, min_val, max_val))

            # Latest timestamp
            t_latest = pd.to_datetime(group["event_time"].max())
            # Ensure timezone awareness
            if t_latest.tzinfo is None:
                t_latest = t_latest.tz_localize(timezone.utc)
            as_of_tz = as_of if as_of.tzinfo is not None else as_of.replace(tzinfo=timezone.utc)

            staleness_h = max(0.0, (as_of_tz - t_latest).total_seconds() / 3600.0)

            # Staleness-inflated variance
            base_var = float(np.var(cleaned_vals)) if len(cleaned_vals) > 1 else 0.05
            inflated_var = base_var + self._q_drift * staleness_h

            if zid not in results:
                results[zid] = {}

            results[zid][var] = {
                "value": fused_val,
                "variance": inflated_var,
                "staleness_h": staleness_h,
                "quality": float(np.mean(group["quality"]))
            }

        return results
