from __future__ import annotations
import numpy as np
from typing import Dict, Any, List

class HospitalSimulator:
    """
    Hospital M/M/c/K queuing, acute ED arrivals, ICU strain, regional diversion, and backup power buffer.
    """
    def __init__(self, zones: List[Dict[str, Any]]):
        self.zones = {z["id"]: z for z in zones}
        self.bed_occ = {z["id"]: 72.0 for z in zones}
        self.icu_occ = {z["id"]: 65.0 for z in zones}
        self.gen_hours = {z["id"]: 48.0 for z in zones}

    def step(
        self,
        t_h: int,
        ems_states: Dict[str, Dict[str, float]],
        hlt_states: Dict[str, Dict[str, float]],
        pwr_states: Dict[str, Dict[str, float]],
        air_states: Dict[str, Dict[str, float]],
        interventions_active: List[str],
        rng: np.random.Generator
    ) -> Dict[str, Dict[str, float]]:
        outputs = {}
        icu_expansion = 1.35 if "surge_icu_capacity" in interventions_active else 1.0
        gen_boost = 36.0 if "hospital_backup_generators" in interventions_active else 0.0

        for zid in self.zones:
            ems_rate = ems_states.get(zid, {}).get("call_rate_per_k", 1.2)
            syndromic = hlt_states.get(zid, {}).get("ed_syndromic_count", 5.0)
            pwr_out = pwr_states.get(zid, {}).get("customers_out_pct", 0.0)
            gas_conc = air_states.get(zid, {}).get("concentration_index", 0.0)

            # ED arrivals driven by emergency incidents, epidemic presentations, and toxic exposure
            toxic_arrivals = max(0.0, (gas_conc - 0.8) * 12.0)
            arrivals = 12.0 + 3.5 * ems_rate + 0.15 * syndromic + toxic_arrivals + rng.normal(0, 1.0)
            arrivals = max(2.0, arrivals)

            # Inpatient and ICU occupancy evolution
            net_inflow = (arrivals - 14.0) * 0.45
            self.bed_occ[zid] = float(np.clip(self.bed_occ[zid] + net_inflow - 0.2, 35.0, 140.0))
            
            # ICU evolution with expansion buffer
            effective_icu = (self.icu_occ[zid] + net_inflow * 0.25) / icu_expansion
            self.icu_occ[zid] = float(np.clip(effective_icu, 20.0, 130.0))

            # Backup generator fuel burn when grid power is lost
            if pwr_out >= 25.0:
                self.gen_hours[zid] = max(0.0, self.gen_hours[zid] - 1.0)
            else:
                self.gen_hours[zid] = min(72.0 + gen_boost, self.gen_hours[zid] + 0.5)

            outputs[zid] = {
                "bed_occupancy_pct": self.bed_occ[zid],
                "icu_occupancy_pct": self.icu_occ[zid],
                "ed_arrivals_per_h": float(arrivals),
                "generator_hours_rem": float(self.gen_hours[zid])
            }

        return outputs
