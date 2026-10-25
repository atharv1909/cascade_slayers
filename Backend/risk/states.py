from __future__ import annotations
from typing import Dict, Any, List, Optional
import yaml
from harness.schema import RiskState, ConfidenceLevel

class RiskStateMachine:
    """
    Manages 4-state risk mapping (NORMAL, WATCH, HIGH RISK, CRITICAL)
    with strict directional hysteresis to eliminate rapid flapping.
    """
    def __init__(self, thresholds_yaml: Optional[str] = None):
        from harness.paths import get_config_path
        if thresholds_yaml is None:
            thresholds_yaml = get_config_path("thresholds.yaml")
        with open(thresholds_yaml, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)["risk_mapping"]

        self.tau_W = cfg.get("tau_W", 0.20)
        self.tau_H = cfg.get("tau_H", 0.40)
        self.tau_C = cfg.get("tau_C", 0.60)
        self.downgrade_ticks_needed = cfg.get("downgrade_hysteresis_ticks", 2)

        # Hysteresis memory: entity_id -> (current_state, consecutive_below_ticks)
        self._zone_states: Dict[str, RiskState] = {}
        self._zone_downgrade_counters: Dict[str, int] = {}
        self._city_state = RiskState.NORMAL
        self._city_downgrade_counter = 0

    def evaluate_zone_state(
        self,
        zone_id: str,
        p_cdf: Dict[str, float],
        has_critical_active: bool,
        evidence_coverage: float
    ) -> Tuple[RiskState, ConfidenceLevel, str]:
        """
        Evaluates risk state and confidence for a specific zone.
        Upgrades immediately; downgrades require 2 consecutive ticks.
        """
        p12 = p_cdf.get("12", 0.0)
        p24 = p_cdf.get("24", 0.0)
        p72 = p_cdf.get("72", 0.0)

        # Evaluate target state
        if has_critical_active or p12 >= self.tau_C:
            target = RiskState.CRITICAL
            reason = "Active failure event or P(critical <= 12h) >= 0.60"
        elif p24 >= self.tau_H:
            target = RiskState.HIGH_RISK
            reason = "P(critical <= 24h) >= 0.40"
        elif p72 >= self.tau_W:
            target = RiskState.WATCH
            reason = "P(critical <= 72h) >= 0.20"
        else:
            target = RiskState.NORMAL
            reason = "All horizon probabilities within nominal baseline"

        # Apply hysteresis
        state_ranks = {
            RiskState.NORMAL: 0,
            RiskState.WATCH: 1,
            RiskState.HIGH_RISK: 2,
            RiskState.CRITICAL: 3
        }

        current = self._zone_states.get(zone_id, RiskState.NORMAL)
        current_rank = state_ranks[current]
        target_rank = state_ranks[target]

        if target_rank >= current_rank:
            # Immediate upgrade
            final_state = target
            self._zone_downgrade_counters[zone_id] = 0
        else:
            # Downgrade with hysteresis
            counter = self._zone_downgrade_counters.get(zone_id, 0) + 1
            self._zone_downgrade_counters[zone_id] = counter
            if counter >= self.downgrade_ticks_needed:
                final_state = target
                self._zone_downgrade_counters[zone_id] = 0
            else:
                final_state = current # retain elevated state until confirmed

        self._zone_states[zone_id] = final_state

        # Confidence level
        if evidence_coverage >= 0.80:
            confidence = ConfidenceLevel.HIGH
        elif evidence_coverage >= 0.50:
            confidence = ConfidenceLevel.MED
        else:
            confidence = ConfidenceLevel.LOW

        return final_state, confidence, reason

    def evaluate_city_state(
        self,
        p_cascade_24h: float,
        p_cascade_48h: float,
        zone_states: List[RiskState],
        evidence_coverage: float
    ) -> Tuple[RiskState, ConfidenceLevel]:
        critical_count = sum(1 for s in zone_states if s == RiskState.CRITICAL)
        high_count = sum(1 for s in zone_states if s in [RiskState.HIGH_RISK, RiskState.CRITICAL])

        if p_cascade_24h >= 0.50 or critical_count >= 3:
            city_target = RiskState.CRITICAL
        elif p_cascade_48h >= 0.35 or high_count >= 4:
            city_target = RiskState.HIGH_RISK
        elif any(s != RiskState.NORMAL for s in zone_states):
            city_target = RiskState.WATCH
        else:
            city_target = RiskState.NORMAL

        confidence = (
            ConfidenceLevel.HIGH if evidence_coverage >= 0.80
            else (ConfidenceLevel.MED if evidence_coverage >= 0.50 else ConfidenceLevel.LOW)
        )
        return city_target, confidence
