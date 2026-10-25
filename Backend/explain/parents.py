from __future__ import annotations
from typing import Dict, Any, List, Tuple
import numpy as np
import torch
from cascade.hawkes import DiscreteHawkesGLM

def compute_hawkes_parent_attribution(
    model: DiscreteHawkesGLM,
    convolved_history: torch.Tensor,
    target_layer: str
) -> List[Dict[str, Any]]:
    """
    Computes exact mathematical parent attribution for target_layer under the Hawkes GLM.
    Attribution share = (A[i, j, :] * C[j, :]).sum() / lambda_i
    Ranks which upstream failures are physically driving risk at this node.
    """
    if target_layer not in model.layer_to_idx:
        return []

    i = model.layer_to_idx[target_layer]
    with torch.no_grad():
        intensities = model.forward(convolved_history) # shape (1, num_layers)
        lambda_i = float(intensities[0, i])

        A_eff = model.A # (num_layers, num_layers, num_bases)
        # Contribution from each upstream layer j
        # C has shape (1, num_layers, num_bases)
        contributions = []
        for j, src_layer in enumerate(model.layers):
            if src_layer == target_layer:
                continue
            exc_ij = float(torch.sum(A_eff[i, j, :] * convolved_history[0, j, :]))
            share = (exc_ij / lambda_i) if lambda_i > 0 else 0.0
            if exc_ij > 0.01:
                contributions.append({
                    "upstream_layer": src_layer,
                    "intensity_contribution": round(float(exc_ij), 3),
                    "share_pct": round(float(share * 100.0), 1)
                })

        # Sort by highest driving share
        contributions.sort(key=lambda x: x["intensity_contribution"], reverse=True)
        return contributions
