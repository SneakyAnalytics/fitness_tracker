"""Helpers for comparing two rides: smoothed, evenly spaced power and heart-rate series."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def smooth(values: List[Optional[float]], window: int) -> List[Optional[float]]:
    """Trailing moving average over `window` samples; gaps (None) are skipped, not counted as zero."""
    window = max(1, window)
    out: List[Optional[float]] = []
    for i in range(len(values)):
        chunk = [v for v in values[max(0, i - window + 1): i + 1] if v is not None]
        out.append(sum(chunk) / len(chunk) if chunk else None)
    return out


def resample(values: List[Optional[float]], step: int) -> List[Optional[int]]:
    """One point per `step` samples (the mean of each block), rounded to whole units."""
    step = max(1, step)
    out: List[Optional[int]] = []
    for i in range(0, len(values), step):
        chunk = [v for v in values[i: i + step] if v is not None]
        out.append(round(sum(chunk) / len(chunk)) if chunk else None)
    return out


def ride_series(fit_data: Dict[str, Any], step: int = 10, smooth_window: int = 30) -> Dict[str, Any]:
    """Power (smoothed) and heart rate (lightly smoothed) at one point per `step` seconds, plus a summary."""
    power = (fit_data.get("power_metrics") or {}).get("power_series") or (fit_data.get("time_series") or {}).get("power") or []
    hr = (fit_data.get("hr_metrics") or {}).get("hr_series") or (fit_data.get("time_series") or {}).get("hr") or []
    pm, hm = fit_data.get("power_metrics") or {}, fit_data.get("hr_metrics") or {}
    r = lambda v, n=0: None if v is None else round(v, n)   # noqa: E731
    return {
        "step_sec": step,
        "duration_sec": fit_data.get("duration_seconds") or max(len(power), len(hr)),
        "power": resample(smooth(power, smooth_window), step) if power else [],
        "hr": resample(smooth(hr, 5), step) if hr else [],
        "summary": {
            "avg_power": r(pm.get("average_power")), "np": r(pm.get("normalized_power")),
            "max_power": r(pm.get("max_power")), "intensity_factor": r(pm.get("intensity_factor"), 2),
            "tss": r(pm.get("tss") or (fit_data.get("metrics") or {}).get("tss"), 1),
            "avg_hr": r(hm.get("average_hr")), "max_hr": r(hm.get("max_hr")),
        },
    }
