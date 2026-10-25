from __future__ import annotations
import math
import numpy as np
from typing import Dict, Any, Tuple

def simulate_wx(
    t_h: int,
    scenario_cfg: Dict[str, Any],
    rng: np.random.Generator
) -> Dict[str, float]:
    """
    Simulates weather variables:
    rain_mm_h, temp_c, rh_pct, wind_speed_mps, wind_dir_deg, wbgt_c
    Generates diurnal cycles + storm/heat dome forcing.
    """
    scenario_id = scenario_cfg.get("id", "flood")
    trig = scenario_cfg.get("trigger_generator", {})
    onset_h = trig.get("onset_hour", 48)

    # Diurnal temperature cycle (25C to 34C base)
    diurnal = math.sin((t_h - 9) * 2 * math.pi / 24.0)
    base_temp = 29.5 + 4.5 * diurnal + rng.normal(0, 0.4)
    base_rh = 75.0 - 15.0 * diurnal + rng.normal(0, 2.0)
    base_wind = 4.0 + 1.5 * diurnal + rng.normal(0, 0.5)
    wind_dir = 240.0 + rng.normal(0, 15.0)  # SW monsoon default

    rain_mm_h = 0.0

    if scenario_id in ["flood", "compound_a"]:
        duration = trig.get("duration_h", 36)
        peak = trig.get("peak_intensity_mm_h", trig.get("rain_peak_mm_h", 80.0))
        if onset_h <= t_h <= onset_h + duration:
            progress = (t_h - onset_h) / duration
            # Gamma / bell curve rain envelope
            intensity = peak * math.sin(progress * math.pi) ** 1.5
            rain_mm_h = max(0.0, float(intensity + rng.normal(0, 4.0)))
            base_rh = min(100.0, base_rh + 20.0)
            base_temp -= 3.5

    elif scenario_id == "heat":
        duration = trig.get("duration_h", 96)
        peak_temp = trig.get("peak_temp_c", 44.0)
        if onset_h <= t_h <= onset_h + duration:
            progress = (t_h - onset_h) / duration
            heat_lift = (peak_temp - 29.5) * math.sin(progress * math.pi) ** 0.8
            base_temp += heat_lift
            base_rh = min(85.0, max(45.0, base_rh + 10.0))

    # Stull wet-bulb approximation for WBGT calculation
    tw = (
        base_temp * math.atan(0.151977 * math.sqrt(base_rh + 8.313659))
        + math.atan(base_temp + base_rh)
        - math.atan(base_rh - 1.676331)
        + 0.00391838 * (base_rh ** 1.5) * math.atan(0.023101 * base_rh)
        - 4.686035
    )
    # WBGT outdoor simplified estimation: 0.7 Tw + 0.2 Tg (approx T) + 0.1 Td
    wbgt_c = 0.7 * tw + 0.3 * base_temp

    return {
        "rain_mm_h": float(np.clip(rain_mm_h, 0.0, 250.0)),
        "temp_c": float(np.clip(base_temp, 15.0, 55.0)),
        "rh_pct": float(np.clip(base_rh, 10.0, 100.0)),
        "wind_speed_mps": float(np.clip(base_wind, 0.5, 45.0)),
        "wind_dir_deg": float(wind_dir % 360.0),
        "wbgt_c": float(np.clip(wbgt_c, 15.0, 45.0))
    }

def generate_weather_forecast(
    as_of_h: int,
    lead_h: int,
    true_wx_fn,
    rng: np.random.Generator
) -> Dict[str, float]:
    """
    Simulates weather forecast products issued at as_of_h for valid_for = as_of_h + lead_h.
    CRITICAL: Enforces lead-dependent error growth (sigma rises roughly linearly with lead).
    The model receives this covariate, NOT the realized future!
    """
    target_h = as_of_h + lead_h
    realized = true_wx_fn(target_h)

    # Lead dependent error growth
    error_scale = 0.08 * (lead_h / 24.0)

    forecast_rain = max(0.0, realized["rain_mm_h"] + rng.normal(0, (lead_h ** 0.6) * 1.8))
    forecast_temp = realized["temp_c"] + rng.normal(0, error_scale * 3.5)
    forecast_rh = np.clip(realized["rh_pct"] + rng.normal(0, error_scale * 8.0), 10.0, 100.0)

    return {
        "rain_mm_h": float(forecast_rain),
        "temp_c": float(forecast_temp),
        "rh_pct": float(forecast_rh)
    }
