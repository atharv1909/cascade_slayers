from __future__ import annotations
import math
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd

class CRHTruthDiscovery:
    """
    Conflict Resolution on Heterogeneous Data (CRH) Expectation-Maximization algorithm.
    Discovers source reliability without ground truth labels.
    """
    def __init__(self, lambda_loss: float = 1.8, forgetting_rate: float = 0.98):
        self.lambda_loss = lambda_loss
        self.forgetting_rate = forgetting_rate
        # Source reliability history: source_id -> list of float
        self.reliability_history: Dict[str, List[float]] = {}
        self.current_reliabilities: Dict[str, float] = {}

    def run_discovery(
        self,
        events_df: pd.DataFrame,
        as_of: datetime,
        iterations: int = 4
    ) -> Dict[str, float]:
        """
        Runs CRH EM over rolling 24-hour observation window.
        Returns: { source_id: reliability_score in [0.05, 1.0] }
        """
        if events_df.empty:
            return self.current_reliabilities

        as_of_tz = as_of if as_of.tzinfo is not None else as_of.replace(tzinfo=timezone.utc)
        window_start = as_of_tz - timedelta(hours=24)

        # Filter window
        df_win = events_df[pd.to_datetime(events_df["event_time"]).dt.tz_localize(None) >= window_start.replace(tzinfo=None)]
        if df_win.empty:
            return self.current_reliabilities

        sources = df_win["source_id"].unique().tolist()
        # Initialize reliabilities
        weights = {s: self.current_reliabilities.get(s, 0.90) for s in sources}

        for it in range(iterations):
            source_errors: Dict[str, List[float]] = {s: [] for s in sources}

            # Group claims by (zone_id, variable, 1h-bucket)
            for (zid, var), group in df_win.groupby(["zone_id", "variable"]):
                if len(group) == 1:
                    continue

                vals = group["value"].values
                srcs = group["source_id"].values
                w_arr = np.array([weights.get(s, 0.5) for s in srcs])
                w_norm = w_arr / max(1e-6, w_arr.sum())

                # Weighted consensus (median approximation)
                consensus = float(np.sum(vals * w_norm))
                scale = float(max(1.0, np.std(vals)))

                for s, v in zip(srcs, vals):
                    err = abs(v - consensus) / scale
                    source_errors[s].append(err)

            # Update weights: r_s = exp(-lambda * mean_loss)
            for s in sources:
                errors = source_errors[s]
                if errors:
                    mean_loss = float(np.mean(errors))
                    updated_r = float(np.exp(-self.lambda_loss * mean_loss))
                    # Apply exponential smoothing with previous step
                    prev_r = weights.get(s, 0.90) * self.forgetting_rate
                    weights[s] = float(np.clip(0.3 * updated_r + 0.7 * prev_r, 0.05, 1.0))

        self.current_reliabilities = weights

        # Record history
        for s, r in weights.items():
            if s not in self.reliability_history:
                self.reliability_history[s] = []
            self.reliability_history[s].append(round(r, 3))
            if len(self.reliability_history[s]) > 24:
                self.reliability_history[s].pop(0)

        return self.current_reliabilities

    def get_source_details(self) -> List[Dict[str, Any]]:
        """Returns structured details for /v1/sources/reliability endpoint."""
        details = []
        for s, r in self.current_reliabilities.items():
            hist = self.reliability_history.get(s, [r])
            details.append({
                "source_id": s,
                "source_type": "sensor" if "sensor" in s else ("feed" if "feed" in s or "imdf" in s else "citizen"),
                "layer": s.split("_")[0].upper() if "_" in s else "COM",
                "reliability": round(r, 3),
                "staleness_h": 0.2,
                "quarantined": bool(r < 0.25),
                "history": hist[-10:] if len(hist) >= 10 else hist
            })
        return details
