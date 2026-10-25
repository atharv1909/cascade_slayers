from __future__ import annotations
import math
import os
import json
import logging
from typing import Dict, Any, List, Tuple, Optional
from harness.paths import get_project_root
import numpy as np

logger = logging.getLogger(__name__)

class EpidemicTypeAftershockSequence:
    """
    ETAS (Epidemic-Type Aftershock Sequence) point process for seismic risk.
    Models aftershock triggering rates and cumulative magnitude probabilities.
    Supports loading fitted parameters from Kaggle NB05 checkpoint JSON.
    """
    def __init__(
        self,
        mu: float = 0.05,
        K: float = 14.5,
        alpha: float = 1.05,
        c: float = 0.45,
        p: float = 1.10,
        m0: float = 3.5,
        checkpoint_path: Optional[str] = None
    ):
        self.mu = mu
        self.K = K
        self.alpha = alpha
        self.c = c
        self.p = p
        self.m0 = m0
        self.b_value = 1.0
        self.is_real_params = False

        if checkpoint_path:
            self.load_from_checkpoint(checkpoint_path)

    def load_from_checkpoint(self, checkpoint_path: Optional[str] = None) -> bool:
        """
        Loads fitted ETAS parameters from JSON checkpoint file.
        """
        candidate_paths = []
        if checkpoint_path:
            candidate_paths.append(checkpoint_path)

        search_roots = [
            os.path.join(get_project_root(), 'runs', 'models'),
            os.path.join(get_project_root(), 'models'),
            os.path.join(get_project_root(), 'runs', 'kaggle_output'),
            os.path.join(get_project_root(), 'training code', 'etas_model'),
            './runs/models',
            './models'
        ]
        for root in search_roots:
            candidate_paths.append(os.path.join(root, 'etas_params.json'))

        for path in candidate_paths:
            if os.path.isfile(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    self.mu = float(data.get('mu', self.mu))
                    self.K = float(data.get('K', self.K))
                    self.alpha = float(data.get('alpha', self.alpha))
                    self.c = float(data.get('c', self.c))
                    self.p = float(data.get('p', self.p))
                    self.m0 = float(data.get('m0', data.get('m_ref', self.m0)))
                    self.b_value = float(data.get('b', self.b_value))
                    self.is_real_params = True
                    print(f"[ETAS] Loaded fitted parameters from {path}: mu={self.mu}, K={self.K}, p={self.p}")
                    return True
                except Exception as e:
                    print(f"[ETAS] Could not load parameters from {path}: {e}")

        return False

    def compute_rate(self, t_hours: float, mainshock_mag: float = 6.4, mainshock_t: float = 0.0) -> float:
        """Instantaneous aftershock rate lambda(t) at time t in hours."""
        if t_hours < mainshock_t:
            return self.mu
        dt = t_hours - mainshock_t
        productivity = self.K * (10.0 ** (self.alpha * (mainshock_mag - self.m0)))
        omori_kernel = productivity / ((dt + self.c) ** self.p)
        return self.mu + omori_kernel

    def compute_aftershock_probabilities(
        self,
        as_of_h: float,
        mainshock_mag: float = 6.4,
        mainshock_t: float = 0.0
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculates aftershock probability for horizons h in [1, 3, 6, 12, 24, 48, 72]
        across magnitude thresholds M >= 4.0, M >= 5.0, M >= 6.0.
        P(>=1 event in [t, t+h]) = 1 - exp(-integral lambda dt)
        """
        results = {}
        horizons = [1, 3, 6, 12, 24, 48, 72]

        for h in horizons:
            t_eval = np.linspace(as_of_h, as_of_h + h, 50)
            rates = [self.compute_rate(t, mainshock_mag, mainshock_t) for t in t_eval]
            expected_total_events = float(np.trapz(rates, t_eval))

            p_m4 = float(1.0 - np.exp(-expected_total_events * (10.0 ** (-self.b_value * (4.0 - self.m0)))))
            p_m5 = float(1.0 - np.exp(-expected_total_events * (10.0 ** (-self.b_value * (5.0 - self.m0)))))
            p_m6 = float(1.0 - np.exp(-expected_total_events * (10.0 ** (-self.b_value * (6.0 - self.m0)))))

            results[str(h)] = {
                "p_m4": round(float(np.clip(p_m4, 0.0, 1.0)), 4),
                "p_m5": round(float(np.clip(p_m5, 0.0, 1.0)), 4),
                "p_m6": round(float(np.clip(p_m6, 0.0, 1.0)), 4),
                "expected_events": round(expected_total_events, 2)
            }

        return results
