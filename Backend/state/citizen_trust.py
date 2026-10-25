from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd

class CitizenTrustManager:
    """
    Manages citizen reporter reputation using Beta-Bernoulli distributions,
    detects coordinated bot bursts, and quarantines uncorroborated clusters.
    """
    def __init__(self):
        # user_id -> (alpha, beta)
        self.reporters: Dict[str, Tuple[float, float]] = {}
        self.quarantined_clusters: List[Dict[str, Any]] = []

    def get_trust(self, reporter_id: str) -> float:
        """Expected trust value: alpha / (alpha + beta)"""
        alpha, beta = self.reporters.get(reporter_id, (2.0, 2.0))
        return alpha / (alpha + beta)

    def process_reports(
        self,
        reports_df: pd.DataFrame,
        sensor_evidence_by_zone: Dict[str, float],
        as_of: datetime
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Processes citizen report events within 30-min spatial clusters.
        Returns: (accepted_reports, quarantined_bursts)
        """
        accepted = []
        quarantined = []

        if reports_df.empty:
            return accepted, quarantined

        # Cluster by (zone_id, 30-min time window)
        reports_df = reports_df.copy()
        reports_df["cluster_time"] = pd.to_datetime(reports_df["event_time"]).dt.floor("30min")

        for (zid, c_time), group in reports_df.groupby(["zone_id", "cluster_time"]):
            n_reports = len(group)
            reporters_in_group = group["source_id"].tolist()
            mean_trust = np.mean([self.get_trust(r) for r in reporters_in_group])
            sensor_support = sensor_evidence_by_zone.get(zid, 0.0)

            # Burst Detection Rule:
            # High burst (>= 15 reports) from low/neutral trust accounts with NO sensor corroboration
            if n_reports >= 15 and mean_trust <= 0.52 and sensor_support < 0.15:
                cluster_info = {
                    "zone_id": zid,
                    "cluster_time": c_time.isoformat(),
                    "report_count": n_reports,
                    "mean_trust": round(float(mean_trust), 3),
                    "reason": "Coordinated uncorroborated bot burst. Sensor confirms normal state.",
                    "status": "QUARANTINED"
                }
                quarantined.append(cluster_info)
                self.quarantined_clusters.append(cluster_info)

                # Penalize reporters with Beta updates: +1 beta
                for r in reporters_in_group:
                    a, b = self.reporters.get(r, (2.0, 2.0))
                    self.reporters[r] = (a, b + 1.0)
            else:
                # Corroborated or legitimate reports
                corroboration_factor = 1.0 - (0.5 ** min(n_reports, 5))
                for idx, row in group.iterrows():
                    rep_id = row["source_id"]
                    trust = self.get_trust(rep_id)
                    weight = trust * corroboration_factor

                    accepted.append({
                        "event_id": row["event_id"],
                        "zone_id": zid,
                        "weight": round(float(weight), 3),
                        "trust": round(float(trust), 3),
                        "value": float(row["value"])
                    })

                    # If supported by sensors, award +1 alpha
                    if sensor_support > 0.40:
                        a, b = self.reporters.get(rep_id, (2.0, 2.0))
                        self.reporters[rep_id] = (a + 1.0, b)

        return accepted, quarantined
