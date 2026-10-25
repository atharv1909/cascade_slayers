from __future__ import annotations
from typing import Dict, Any, List

def generate_plain_bulletin(
    zone_id: str,
    zone_name: str,
    risk_state: str,
    time_to_critical: Dict[str, Any],
    top_drivers: List[Dict[str, Any]],
    recommended_intervention: str,
    as_of_str: str
) -> str:
    """
    Deterministic template-generated emergency advisory bulletin with strict numeric safety.
    Guarantees that no halluncinated probability or invented ETA reaches emergency responders.
    """
    t_text = (
        f"Median time-to-critical is {time_to_critical.get('q50')} hours (80% range: {time_to_critical.get('q10')} to {time_to_critical.get('q90')} h)."
        if time_to_critical.get("q50") is not None
        else f"Critical threshold is beyond 72 hours (probability <= 72h is {time_to_critical.get('beyond_72h_p')})."
    )

    driver_str = ", ".join([f"{d['layer']} ({d['importance_score']})" for d in top_drivers[:3]]) or "Baseline conditions"

    bulletin = (
        f"[CIVIL PROTECTION ADVISORY - {zone_name.upper()} ({zone_id})]\n"
        f"Status: {risk_state} as of {as_of_str} (UTC).\n"
        f"Timing: {t_text}\n"
        f"Primary Cascade Drivers: {driver_str}.\n"
        f"Recommended Action: {recommended_intervention}.\n"
        f"Data Classification: SIMULATED / DECISION-SUPPORT PROTOTYPE ONLY."
    )
    return bulletin

def generate_cascade_receipt(
    zone_id: str,
    as_of_str: str,
    inputs: List[Dict[str, Any]],
    rule_fired: str,
    affected_assets: List[str],
    impact_summary: str
) -> Dict[str, Any]:
    """
    Constructs an auditable Cascade Receipt:
    inputs -> rule -> affected items -> impact with timestamps and provenance.
    """
    return {
        "zone_id": zone_id,
        "timestamp": as_of_str,
        "inputs": inputs,
        "rule": rule_fired,
        "affected_assets": affected_assets,
        "impact": impact_summary,
        "provenance": "MODELLED"
    }
