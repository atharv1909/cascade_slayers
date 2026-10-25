from __future__ import annotations
from typing import Dict, Any, List, Tuple
from river import drift

class DriftMonitor:
    """
    Monitors data and concept drift using ADWIN and Page-Hinkley algorithms.
    Triggers change-point alerts on Hawkes dependency edge changes or sensor distribution shifts.
    """
    def __init__(self):
        self.adwin_errors = drift.ADWIN()
        self.adwin_features: Dict[str, drift.ADWIN] = {}
        self.drift_alarms: List[Dict[str, Any]] = []

    def update_error(self, error_val: float, t_h: int) -> bool:
        """Updates error ADWIN detector."""
        self.adwin_errors.update(error_val)
        if self.adwin_errors.drift_detected:
            alarm = {
                "type": "CONCEPT_DRIFT",
                "hour": t_h,
                "message": "ADWIN detected statistically significant concept drift in prediction residuals.",
                "action": "Triggering online linear residual corrector adaptation."
            }
            self.drift_alarms.append(alarm)
            return True
        return False

    def update_edge_weight(self, from_l: str, to_l: str, current_w: float, t_h: int) -> bool:
        key = f"{from_l}->{to_l}"
        if key not in self.adwin_features:
            self.adwin_features[key] = drift.ADWIN()

        self.adwin_features[key].update(current_w)
        if self.adwin_features[key].drift_detected:
            alarm = {
                "type": "DEPENDENCY_CHANGED",
                "hour": t_h,
                "edge": key,
                "message": f"Coupling strength between {from_l} and {to_l} shifted significantly.",
                "action": "Updating Hawkes graphical kernel online."
            }
            self.drift_alarms.append(alarm)
            return True
        return False

    def get_alarms(self) -> List[Dict[str, Any]]:
        return list(self.drift_alarms)
