from __future__ import annotations
import math
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import yaml
from harness.schema import CanonicalEvent, SourceType, LayerEnum

class FaultInjector:
    """
    Wraps the raw event stream and injects controlled data faults F0 through F5.
    Preserves reproducibility via seeded PRNG.
    """
    def __init__(self, config_path: Optional[str] = None):
        from harness.paths import get_config_path
        if config_path is None:
            config_path = get_config_path("faults.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)["profiles"]

    def apply_faults(
        self,
        events: List[CanonicalEvent],
        profile_name: str = "F0",
        seed: int = 42
    ) -> List[CanonicalEvent]:
        if profile_name not in self.config:
            raise ValueError(f"Unknown fault profile: {profile_name}")

        cfg = self.config[profile_name]
        rng = random.Random(seed)

        dropout_rate = cfg.get("dropout_rate", 0.0)
        blackout_h = cfg.get("blackout_hours", 0)
        latency_mean = cfg.get("latency_mean_h", 0.05)
        latency_sigma = cfg.get("latency_sigma", 0.1)
        stuck_at_frac = cfg.get("stuck_at_fraction", 0.0)
        bias_frac = cfg.get("bias_fraction", 0.0)
        bias_sigma = cfg.get("bias_magnitude_sigma", 2.0)
        adversarial = cfg.get("adversarial_reports", False)
        burst_size = cfg.get("adversarial_burst_size", 0)
        target_zone = cfg.get("adversarial_target_zone", "z09_kalina_campus")

        # Pick a critical source for blackout if applicable
        all_sources = sorted(list(set(e.source_id for e in events)))
        blackout_source = all_sources[0] if all_sources and blackout_h > 0 else None
        blackout_start = events[0].event_time + timedelta(hours=60) if events else None
        blackout_end = blackout_start + timedelta(hours=blackout_h) if blackout_start else None

        # Pick stuck-at and biased sources
        k_stuck = int(len(all_sources) * stuck_at_frac)
        k_bias = int(len(all_sources) * bias_frac)
        stuck_sources = set(rng.sample(all_sources, k_stuck)) if all_sources and k_stuck > 0 else set()
        bias_sources = set(rng.sample(all_sources, k_bias)) if all_sources and k_bias > 0 else set()

        processed: List[CanonicalEvent] = []

        for ev in events:
            # Check blackout
            if blackout_source and ev.source_id == blackout_source and blackout_start and blackout_end:
                if blackout_start <= ev.event_time <= blackout_end:
                    continue  # Dropped during blackout

            # Random dropout
            if dropout_rate > 0 and rng.random() < dropout_rate:
                continue

            ev_copy = ev.model_copy(deep=True)

            # Latency and delay (out of order ingest)
            delay_h = max(0.01, rng.lognormvariate(math.log(max(0.02, latency_mean)), latency_sigma))
            ev_copy.ingest_time = ev_copy.event_time + timedelta(hours=delay_h)

            # Stuck-at fault
            if ev.source_id in stuck_sources:
                ev_copy.value = 0.0
                ev_copy.quality = 0.4

            # Bias drift fault
            if ev.source_id in bias_sources:
                bias_val = rng.gauss(0.0, bias_sigma)
                ev_copy.value = max(0.0, ev_copy.value + bias_val)
                ev_copy.quality = 0.5

            processed.append(ev_copy)

        # Adversarial coordinated burst injection
        if adversarial and burst_size > 0 and processed:
            burst_start = processed[0].event_time + timedelta(hours=70)
            for i in range(burst_size):
                rpt_time = burst_start + timedelta(minutes=rng.uniform(0, 30))
                fake_event = CanonicalEvent(
                    event_id=f"adv_report_{profile_name}_{i}_{rpt_time.timestamp()}",
                    source_id=f"fake_citizen_{rng.randint(1000, 9999)}",
                    source_type=SourceType.CITIZEN,
                    layer=LayerEnum.COM,
                    zone_id=target_zone,
                    variable="citizen_reports_rate",
                    value=float(rng.randint(25, 60)),
                    event_time=rpt_time,
                    ingest_time=rpt_time + timedelta(minutes=1),
                    quality=0.2,
                    meta={"bot_net": True, "text": "Urgent! Extreme flash flood trapped on CST Road!"}
                )
                processed.append(fake_event)

        # Sort by ingest_time to mirror real arrival stream
        processed.sort(key=lambda x: x.ingest_time)
        return processed
