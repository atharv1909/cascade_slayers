from __future__ import annotations
from typing import Dict, Any, List, Tuple
import networkx as nx
import numpy as np

def detect_feedback_loops(
    layers: List[str],
    adj_matrix: np.ndarray,
    min_gain: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Detects directed cycles in the inter-layer dependency graph.
    Computes loop gain = product of edge weights around cycle.
    Loops with gain >= 1.0 are potentially destabilizing / runaway feedbacks.
    """
    G = nx.DiGraph()
    n = len(layers)

    for i in range(n):
        for j in range(n):
            weight = float(adj_matrix[i, j])
            if weight > 0.05:
                # Edge from layer j to layer i
                G.add_edge(layers[j], layers[i], weight=weight)

    loops = []
    # Find simple cycles up to length 4
    try:
        cycles = list(nx.simple_cycles(G))
    except Exception:
        cycles = []

    for cycle in cycles:
        if len(cycle) < 2 or len(cycle) > 5:
            continue
        # Compute loop gain
        gain = 1.0
        for idx in range(len(cycle)):
            u = cycle[idx]
            v = cycle[(idx + 1) % len(cycle)]
            w = G.get_edge_data(u, v, {}).get("weight", 0.0)
            gain *= w

        if gain >= min_gain:
            loops.append({
                "nodes": cycle,
                "gain": round(float(gain), 3)
            })

    # Sort by descending gain
    loops.sort(key=lambda x: x["gain"], reverse=True)
    return loops
