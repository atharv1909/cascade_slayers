from __future__ import annotations
from typing import Dict, Any, List
from river import linear_model, optim

class OnlineResidualCorrector:
    """
    Online linear corrector trained on realized LightGBM log-odds residuals.
    Allows real online incremental adaptation without retraining the heavy offline tree model.
    """
    def __init__(self, learning_rate: float = 0.05):
        self.model = linear_model.LinearRegression(
            optimizer=optim.SGD(learning_rate),
            loss=optim.losses.Log()
        )
        self.updates_count = 0

    def learn_outcome(self, features: Dict[str, float], actual_onset: int, predicted_prob: float):
        """
        Updates residual model with error between predicted probability and actual realized outcome.
        """
        residual = float(actual_onset - predicted_prob)
        self.model.learn_one(features, residual)
        self.updates_count += 1

    def correct_probability(self, features: Dict[str, float], base_prob: float) -> float:
        """
        Adjusts base probability using learned online residual offset.
        """
        offset = self.model.predict_one(features)
        return float(min(1.0, max(0.0, base_prob + offset * 0.15)))
