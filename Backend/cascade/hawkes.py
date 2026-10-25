from __future__ import annotations
import math
import os
import glob
import logging
from typing import Dict, Any, List, Tuple, Optional
from harness.paths import get_project_root
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)

class DiscreteHawkesGLM(nn.Module):
    """
    Multivariate Discrete-Time Hawkes Process (Point-Process GLM).
    Models inter-layer cascade coupling with lag bases and spatial spillover.
    Supports loading trained checkpoint PyTorch state dictionaries or learned K_ij influence matrices.
    """
    def __init__(self, layers: List[str], lag_bases: List[float] = [2.0, 8.0, 24.0], checkpoint_path: Optional[str] = None):
        super().__init__()
        self.layers = layers
        self.num_layers = len(layers)
        self.layer_to_idx = {l: i for i, l in enumerate(layers)}
        self.lag_bases = torch.tensor(lag_bases, dtype=torch.float32)
        self.num_bases = len(lag_bases)

        # Baseline background intensity mu_i >= 0
        self.raw_mu = nn.Parameter(torch.full((self.num_layers,), -3.0))

        # Adjacency kernel tensor A[i, j, b] >= 0 (influence of j on i at lag basis b)
        self.raw_A = nn.Parameter(torch.randn(self.num_layers, self.num_layers, self.num_bases) * 0.1 - 2.5)

        # Physical impossibility mask: 0 for forbidden, 1 for allowed
        mask = torch.ones(self.num_layers, self.num_layers, self.num_bases)
        wx_idx = self.layer_to_idx.get("WX")
        sei_idx = self.layer_to_idx.get("SEI")
        hos_idx = self.layer_to_idx.get("HOS")

        if wx_idx is not None:
            mask[wx_idx, :, :] = 0.0
            mask[wx_idx, wx_idx, :] = 1.0  # WX self-persistence allowed

        if sei_idx is not None and hos_idx is not None:
            mask[sei_idx, hos_idx, :] = 0.0

        self.register_buffer("mask", mask)
        self.is_real_checkpoint = False

        if checkpoint_path:
            self.load_from_checkpoint(checkpoint_path)

    @property
    def mu(self) -> torch.Tensor:
        return torch.nn.functional.softplus(self.raw_mu)

    @property
    def A(self) -> torch.Tensor:
        return torch.nn.functional.softplus(self.raw_A) * self.mask

    def load_from_checkpoint(self, checkpoint_path: Optional[str] = None) -> bool:
        """
        Loads trained Hawkes weights (.pt) or learned influence matrix (.csv).
        Auto-searches candidate model directories if path is None.
        """
        candidate_paths = []
        if checkpoint_path:
            candidate_paths.append(checkpoint_path)

        search_roots = [
            os.path.join(get_project_root(), 'runs', 'models'),
            os.path.join(get_project_root(), 'models'),
            os.path.join(get_project_root(), 'runs', 'kaggle_output'),
            os.path.join(get_project_root(), 'training code', 'hawkes_model'),
            './runs/models',
            './models'
        ]
        for root in search_roots:
            candidate_paths.extend([
                os.path.join(root, 'hawkes_pooled.pt'),
                os.path.join(root, 'edge_influence_matrix.csv')
            ])

        for path in candidate_paths:
            if os.path.isfile(path):
                try:
                    if path.endswith('.pt'):
                        state = torch.load(path, map_location='cpu')
                        # Check shape compatibility
                        if 'raw_A' in state and state['raw_A'].shape == self.raw_A.shape:
                            self.load_state_dict(state, strict=False)
                            self.is_real_checkpoint = True
                            print(f"[HAWKES] Loaded PyTorch state dict from {path}")
                            return True
                    elif path.endswith('.csv'):
                        df = pd.read_csv(path, index_col=0)
                        # Map influence matrix into raw_A
                        with torch.no_grad():
                            for col in df.columns:
                                for idx in df.index:
                                    src = col.split('_')[0] if '_' in col else col
                                    dst = idx.split('_')[0] if '_' in idx else idx
                                    if src in self.layer_to_idx and dst in self.layer_to_idx:
                                        i = self.layer_to_idx[dst]
                                        j = self.layer_to_idx[src]
                                        val = float(df.loc[idx, col])
                                        self.raw_A[i, j, :] = math.log(max(1e-4, math.exp(val) - 1.0))
                        self.is_real_checkpoint = True
                        print(f"[HAWKES] Loaded influence matrix from {path}")
                        return True
                except Exception as e:
                    print(f"[HAWKES] Checkpoint load failed from {path}: {e}")

        return False

    def compute_integrated_kernel(self) -> np.ndarray:
        """
        Computes integrated kernel K_ij = sum_b A[i, j, b] * tau_b.
        Matrix represents expected direct offspring events of type i generated by event j.
        """
        with torch.no_grad():
            A_curr = self.A.cpu().numpy()
            tau = self.lag_bases.cpu().numpy()
            K = np.sum(A_curr, axis=2)
            return K

    def compute_branching_ratio(self) -> Tuple[float, np.ndarray]:
        """
        Branching ratio rho = spectral radius of integrated kernel K.
        rho >= 1.0 indicates supercritical self-sustaining cascade.
        Returns: (rho, edge_sensitivity_matrix d_rho / d_A)
        """
        K = self.compute_integrated_kernel()
        eigenvalues, r_eigenvectors = np.linalg.eig(K)
        max_idx = np.argmax(np.real(eigenvalues))
        rho = float(np.real(eigenvalues[max_idx]))

        _, l_eigenvectors = np.linalg.eig(K.T)
        v = np.real(r_eigenvectors[:, max_idx])
        u = np.real(l_eigenvectors[:, max_idx])

        denom = np.dot(u, v)
        if abs(denom) > 1e-8:
            sensitivity = np.outer(u, v) / denom
        else:
            sensitivity = np.zeros_like(K)

        return rho, sensitivity

    def forward(self, convolved_history: torch.Tensor) -> torch.Tensor:
        """
        convolved_history: shape (batch, num_layers, num_bases)
        returns intensity lambda: shape (batch, num_layers)
        """
        A_eff = self.A
        exc = torch.einsum("ijk,bjk->bi", A_eff, convolved_history)
        return self.mu + exc

    def compute_loss(self, intensities: torch.Tensor, event_counts: torch.Tensor, l1_lambda: float = 0.01) -> torch.Tensor:
        eps = 1e-6
        nll = torch.sum(intensities - event_counts * torch.log(intensities + eps))
        l1 = l1_lambda * torch.sum(self.A)
        return nll + l1

    def warm_start_prior(self, prior_edges: List[Dict[str, Any]]):
        """Warm-starts A tensor using prior knowledge if no real checkpoint loaded."""
        if self.is_real_checkpoint:
            return
        with torch.no_grad():
            for edge in prior_edges:
                src = edge.get("from")
                dst = edge.get("to")
                lag = edge.get("lag_h", 2)
                if src in self.layer_to_idx and dst in self.layer_to_idx:
                    i = self.layer_to_idx[dst]
                    j = self.layer_to_idx[src]
                    tau_arr = self.lag_bases.numpy()
                    b_idx = int(np.argmin(np.abs(tau_arr - lag)))
                    self.raw_A[i, j, b_idx] = 0.5
