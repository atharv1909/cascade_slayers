from __future__ import annotations
import numpy as np
from typing import Dict, Any, List, Tuple
from sklearn.isotonic import IsotonicRegression

class ProbabilityCalibrator:
    """
    Fits non-parametric isotonic regression calibrators per event type and horizon.
    Computes Expected Calibration Error (ECE) and Brier scores.
    """
    def __init__(self):
        self.calibrators: Dict[str, IsotonicRegression] = {}

    def fit_calibration(self, y_probs: np.ndarray, y_true: np.ndarray, key: str):
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        iso.fit(y_probs, y_true)
        self.calibrators[key] = iso

    def calibrate(self, raw_prob: float, key: str) -> float:
        if key in self.calibrators:
            return float(self.calibrators[key].predict([raw_prob])[0])
        return raw_prob

    @staticmethod
    def compute_ece(probs: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> float:
        """Expected Calibration Error (ECE) across uniform confidence bins."""
        bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
        ece = 0.0
        n = len(probs)
        if n == 0:
            return 0.0

        for i in range(n_bins):
            in_bin = (probs >= bin_edges[i]) & (probs < bin_edges[i + 1])
            count = np.sum(in_bin)
            if count > 0:
                acc = np.mean(labels[in_bin])
                conf = np.mean(probs[in_bin])
                ece += (count / n) * abs(acc - conf)
        return float(ece)

    @staticmethod
    def compute_brier_score(probs: np.ndarray, labels: np.ndarray) -> float:
        """Mean squared error between predicted probabilities and binary outcomes."""
        return float(np.mean((probs - labels) ** 2))
