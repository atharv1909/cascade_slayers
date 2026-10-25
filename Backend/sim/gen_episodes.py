from __future__ import annotations
import os
import json
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from sim.core import CityDigitalTwin
from sim.observe import generate_canonical_events
from harness.faults import FaultInjector
from harness.paths import get_project_root, get_config_path, get_runs_path

def get_scenarios():
    return [
        ("flood", get_config_path("plugins/flood.yaml")),
        ("heat", get_config_path("plugins/heat.yaml")),
        ("grid", get_config_path("plugins/grid.yaml")),
        ("epidemic", get_config_path("plugins/epidemic.yaml")),
        ("quake", get_config_path("plugins/quake.yaml")),
        ("chem", get_config_path("plugins/chem.yaml")),
        ("compound_a", get_config_path("plugins/compound_a.yaml")),
        ("compound_b", get_config_path("plugins/compound_b.yaml")),
    ]

def precompute_all_scenarios(
    output_dir: str = None,
    anchor_city: str = None,
    heldout_city: str = None
):
    """
    Generates and pre-caches offline scenario runs for instant demo loading.
    Generates truth states, issued forecasts, canonical events, and F0-F5 fault variants.
    """
    if output_dir is None:
        output_dir = get_runs_path()
    if anchor_city is None:
        anchor_city = get_config_path("cities/mumbai.yaml")
    if heldout_city is None:
        heldout_city = get_config_path("cities/heldout_city.yaml")

    os.makedirs(output_dir, exist_ok=True)
    start_dt = datetime(2026, 7, 26, 0, 0, 0, tzinfo=timezone.utc)
    injector = FaultInjector()
    rng = np.random.default_rng(42)

    print("Generating simulated episodes for all 6 hazards and compound scenarios...")

    for scen_id, plugin_path in get_scenarios():
        print(f" -> Generating scenario: {scen_id}")
        twin = CityDigitalTwin(anchor_city, plugin_path, seed=42)
        truth_df, fc_df, g_true = twin.run_episode()

        clean_events = generate_canonical_events(truth_df, fc_df, start_dt, rng)

        for fault_prof in ["F0", "F1", "F2", "F3", "F4", "F5"]:
            scen_fault_dir = os.path.join(output_dir, scen_id, fault_prof)
            os.makedirs(scen_fault_dir, exist_ok=True)

            faulty_events = injector.apply_faults(clean_events, profile_name=fault_prof, seed=42)

            # Save canonical events
            events_records = [e.model_dump(mode="json") for e in faulty_events]
            with open(os.path.join(scen_fault_dir, "events.json"), "w", encoding="utf-8") as f:
                json.dump(events_records, f)

            # Save G_true
            with open(os.path.join(scen_fault_dir, "g_true.json"), "w", encoding="utf-8") as f:
                json.dump(g_true, f)

    # Generate Held-out City episode (Flood)
    print(" -> Generating held-out city episode...")
    twin_heldout = CityDigitalTwin(heldout_city, get_config_path("plugins/flood.yaml"), seed=99)
    truth_h, fc_h, g_h = twin_heldout.run_episode()
    events_h = generate_canonical_events(truth_h, fc_h, start_dt, rng)
    h_dir = os.path.join(output_dir, "heldout_city", "F0")
    os.makedirs(h_dir, exist_ok=True)
    with open(os.path.join(h_dir, "events.json"), "w", encoding="utf-8") as f:
        json.dump([e.model_dump(mode="json") for e in events_h], f)

    print("All episode runs successfully precomputed and cached on disk.")

if __name__ == "__main__":
    precompute_all_scenarios()
