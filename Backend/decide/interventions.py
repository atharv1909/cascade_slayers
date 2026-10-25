from __future__ import annotations
from typing import Dict, Any, List, Optional
import yaml

class InterventionCatalog:
    """
    Catalog of modeled emergency interventions.
    Maintains resource pools, deployment leads, effect multipliers, and operational side-effects.
    """
    def __init__(self, yaml_path: Optional[str] = None):
        from harness.paths import get_config_path
        if yaml_path is None:
            yaml_path = get_config_path("interventions.yaml")
        with open(yaml_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        self.resource_pools = cfg.get("resource_pools", {})
        self.interventions = {i["id"]: i for i in cfg.get("interventions", [])}

    def get_interventions_for_hazard(self, hazard_id: str) -> List[Dict[str, Any]]:
        results = []
        for i_id, i_data in self.interventions.items():
            if hazard_id in i_data.get("hazards", []):
                results.append(i_data)
        return results

    def get_all(self) -> List[Dict[str, Any]]:
        return list(self.interventions.values())

    def get_by_id(self, intervention_id: str) -> Optional[Dict[str, Any]]:
        return self.interventions.get(intervention_id)
