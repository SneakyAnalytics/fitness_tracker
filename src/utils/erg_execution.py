"""Deterministic execution scoring: prescribed intervals vs what the FIT file shows.

Execution quality is measured here, not judged by an LLM. The model that writes
the workout narrative receives these numbers as fact.

Alignment, most to least reliable:
  1. FIT laps. Zwift stamps a lap at every ZWO interval boundary (plus usually a
     short trailing lap). Laps are paired with intervals by duration, trying
     every possible count of leading extra laps, and only accepted when the
     durations actually agree.
  2. Time series. Slide the prescribed power profile along the recorded 1 Hz
     power and pick the offset with the smallest error, so a pre-ride spin
     before the workout started does not shift every interval.
"""
from __future__ import annotations

import statistics
from typing import Any, Dict, List, Optional, Tuple

WARMUP_WORDS = ("warmup", "warm up", "warm-up")
COOLDOWN_WORDS = ("cooldown", "cool down", "cool-down")
RECOVERY_WORDS = ("recovery", "rest", "easy")

# Lap durations must agree with the prescription within this fraction on average.
LAP_DURATION_TOLERANCE = 0.10
# Every work interval outside its band by at least this much, in the same
# direction and with little spread, means Zwift's FTP differs from the plan FTP
# (ERG holds fraction x Zwift FTP) rather than an execution problem.
SYSTEMATIC_OFFSET_MIN = 0.02
SYSTEMATIC_OFFSET_MAX_SPREAD = 0.02


def classify_interval(name: str) -> str:
    lowered = (name or "").lower()
    if any(w in lowered for w in WARMUP_WORDS):
        return "WARMUP"
    if any(w in lowered for w in COOLDOWN_WORDS):
        return "COOLDOWN"
    if any(w in lowered for w in RECOVERY_WORDS):
        return "RECOVERY"
    return "WORK"


def resolve_target(power_target: Optional[Dict[str, Any]], ftp: float) -> Tuple[Optional[float], Optional[float], str]:
    """Return (low_watts, high_watts, display) for a prescribed power target."""
    if not power_target:
        return None, None, "—"

    def to_watts(value: float, unit: Optional[str]) -> float:
        return value / 100.0 * ftp if unit == "percent_ftp" else value

    if power_target.get("type") == "range":
        unit = power_target.get("unit", "watts")
        lo = to_watts(float(power_target.get("min", 0)), unit)
        hi = to_watts(float(power_target.get("max", 0)), unit)
        lo, hi = min(lo, hi), max(lo, hi)
        return lo, hi, f"{lo:.0f}-{hi:.0f}W"
    if "start" in power_target and "end" in power_target:
        s, e = power_target["start"], power_target["end"]
        sw = to_watts(float(s.get("value", 0)), s.get("type"))
        ew = to_watts(float(e.get("value", 0)), e.get("type"))
        # Average power over a linear ramp is its midpoint.
        mid = (sw + ew) / 2
        return mid, mid, f"{sw:.0f}→{ew:.0f}W ramp"
    if power_target.get("type") == "percent_ftp":
        w = to_watts(float(power_target.get("value", 0)), "percent_ftp")
        return w, w, f"{power_target.get('value')}% FTP ({w:.0f}W)"
    value = power_target.get("value")
    if value is not None:
        w = float(value)
        return w, w, f"{w:.0f}W"
    return None, None, "—"


def deviation_pct(actual: float, low: float, high: float) -> float:
    """0 inside the target band; otherwise percent beyond the nearest edge."""
    if low <= actual <= high:
        return 0.0
    edge = low if actual < low else high
    return (actual - edge) / edge * 100.0 if edge else 0.0


def compliance_flag(dev: float) -> str:
    if abs(dev) <= 5:
        return "on_target"
    if abs(dev) <= 10:
        return "close"
    return "low" if dev < 0 else "high"


def _align_laps(laps: List[Dict[str, Any]], durations: List[int]) -> Optional[List[Optional[Dict[str, Any]]]]:
    """Pair laps with intervals by duration, or None if they don't agree."""
    if not laps or len(laps) < len(durations):
        return None
    best: Optional[Tuple[float, int]] = None
    for lead in range(0, len(laps) - len(durations) + 1):
        window = laps[lead:lead + len(durations)]
        errors = []
        for lap, dur in zip(window, durations):
            lap_dur = lap.get("total_elapsed_time")
            if lap_dur is None or dur <= 0:
                errors.append(1.0)
            else:
                errors.append(abs(float(lap_dur) - dur) / dur)
        err = sum(errors) / len(errors)
        if best is None or err < best[0]:
            best = (err, lead)
    if best is None or best[0] > LAP_DURATION_TOLERANCE:
        return None
    return list(laps[best[1]:best[1] + len(durations)])


def _align_time_series(power: List[Optional[float]], durations: List[int],
                       targets: List[Optional[float]]) -> Tuple[int, List[Optional[float]]]:
    """Find the start offset (seconds) that best fits the prescribed profile."""
    profile: List[Optional[float]] = []
    for dur, tgt in zip(durations, targets):
        profile.extend([tgt] * dur)
    samples = [p if p is not None else 0.0 for p in power]
    slack = max(0, len(samples) - len(profile))
    best_offset, best_err = 0, None
    step = 5 if slack > 120 else 1
    for offset in range(0, slack + 1, step):
        err, n = 0.0, 0
        for i in range(0, len(profile), 10):  # subsample for speed; plenty for alignment
            tgt = profile[i]
            j = offset + i
            if tgt is None or j >= len(samples):
                continue
            err += abs(samples[j] - tgt)
            n += 1
        if n and (best_err is None or err / n < best_err):
            best_offset, best_err = offset, err / n
    averages: List[Optional[float]] = []
    cursor = best_offset
    for dur in durations:
        segment = [p for p in samples[cursor:cursor + dur] if p and p > 0]
        averages.append(sum(segment) / len(segment) if segment else None)
        cursor += dur
    return best_offset, averages


def _interval_points(dev: Optional[float]) -> float:
    if dev is None:
        return 0.0  # not ridden: the session was cut short
    a = abs(dev)
    if a <= 5:
        return 1.0
    if a <= 10:
        return 0.7
    if a <= 20:
        return 0.3
    return 0.0


def compute_execution(proposed_workout: Dict[str, Any], parsed_data: Dict[str, Any],
                      ftp: float) -> Optional[Dict[str, Any]]:
    """Compare prescribed intervals with the ride. Returns None if not comparable."""
    intervals = [iv for iv in (proposed_workout.get("intervals") or []) if int(iv.get("duration", 0) or 0) > 0]
    if not intervals:
        return None

    durations = [int(iv["duration"]) for iv in intervals]
    resolved = [resolve_target(iv.get("powerTarget"), ftp) for iv in intervals]

    actuals: List[Optional[float]]
    aligned_laps = _align_laps(parsed_data.get("laps") or [], durations)
    if aligned_laps is not None:
        alignment = "laps"
        actuals = [float(lap["avg_power"]) if lap.get("avg_power") is not None else None for lap in aligned_laps]
        offset_sec = None
    else:
        series = (parsed_data.get("time_series") or {}).get("power") or []
        timestamps = (parsed_data.get("time_series") or {}).get("timestamps") or []
        if len(series) < 30 or (timestamps and len(series) != len(timestamps)):
            # time_series.power is zero-filtered by the parser when any sample is
            # missing, so it no longer lines up with time; don't guess.
            return None
        alignment = "time_series"
        mids = [((lo + hi) / 2) if lo is not None else None for lo, hi, _ in resolved]
        offset_sec, actuals = _align_time_series(series, durations, mids)

    if all(a is None for a in actuals):
        # No power at all (e.g. outdoor ride without a power meter): not
        # comparable, which is different from "didn't ride the intervals".
        return None

    rows: List[Dict[str, Any]] = []
    for idx, (iv, dur, (lo, hi, display), actual) in enumerate(zip(intervals, durations, resolved, actuals)):
        name = iv.get("name") or f"Interval {idx + 1}"
        dev = deviation_pct(actual, lo, hi) if actual is not None and lo else None
        rows.append({
            "index": idx,
            "name": name,
            "label": classify_interval(name),
            "duration_sec": dur,
            "target_low_w": round(lo, 1) if lo is not None else None,
            "target_high_w": round(hi, 1) if hi is not None else None,
            "target_display": display,
            "actual_avg_w": round(actual, 1) if actual is not None else None,
            "deviation_pct": round(dev, 1) if dev is not None else None,
            "compliance": compliance_flag(dev) if dev is not None else ("missing" if actual is None else None),
        })

    scored = [r for r in rows if r["label"] == "WORK" and r["target_low_w"]]
    if not scored:
        scored = [r for r in rows if r["label"] not in ("WARMUP", "COOLDOWN") and r["target_low_w"]]
    if not scored:
        scored = [r for r in rows if r["target_low_w"]]

    # ERG holds (FTP fraction x Zwift's FTP). A tight, consistent ratio away from
    # 1.0 is an FTP-setting mismatch, not an execution error. Only trust this
    # when laps aligned, i.e. the ride really was the structured Zwift workout.
    systematic_offset = None
    if alignment == "laps":
        devs = [r["deviation_pct"] for r in scored if r["deviation_pct"] is not None]
        if (len(devs) >= 2
                and (all(d < 0 for d in devs) or all(d > 0 for d in devs))
                and min(abs(d) for d in devs) >= SYSTEMATIC_OFFSET_MIN * 100
                and max(devs) - min(devs) <= SYSTEMATIC_OFFSET_MAX_SPREAD * 100):
            systematic_offset = round(statistics.median(devs), 1)

    def score_dev(r: Dict[str, Any]) -> Optional[float]:
        if r["actual_avg_w"] is None:
            return None
        if systematic_offset is None:
            return r["deviation_pct"]
        return r["deviation_pct"] - systematic_offset

    total = sum(r["duration_sec"] for r in scored)
    score = None
    if total:
        score = round(10 * sum(_interval_points(score_dev(r)) * r["duration_sec"] for r in scored) / total, 1)

    completed = sum(1 for r in scored if r["actual_avg_w"] is not None)
    return {
        "alignment": alignment,
        "time_offset_sec": offset_sec,
        "ftp_used": ftp,
        "intervals": rows,
        "scored_intervals": len(scored),
        "completed_intervals": completed,
        "systematic_offset_pct": systematic_offset,
        "execution_score": score,
    }


_FLAG_SYMBOL = {"on_target": "✓", "close": "~", "low": "✗LOW", "high": "↑HIGH", "missing": "—"}


def format_execution_text(result: Dict[str, Any]) -> str:
    """Human/LLM-readable version of compute_execution output."""
    if result["alignment"] == "laps":
        source = "FIT lap markers matched to ZWO intervals by duration"
    else:
        offset = result.get("time_offset_sec") or 0
        source = f"FIT power stream aligned to the prescription (workout started {offset}s into the recording)"
    lines = [
        "\n\n📊 ERG INTERVAL EXECUTION (computed — prescribed vs actual):",
        f"  Source: {source}; targets resolved at FTP {result['ftp_used']:.0f}W",
        "",
    ]
    for r in result["intervals"]:
        mins, secs = divmod(r["duration_sec"], 60)
        head = f"  {r['index'] + 1:2d}. [{r['label']}] {r['name']}: {mins}:{secs:02d} | Target: {r['target_display']}"
        if r["actual_avg_w"] is None:
            lines.append(f"{head} | no power data (not ridden)")
        elif r["deviation_pct"] is None:
            lines.append(f"{head} | Actual: {r['actual_avg_w']:.0f}W")
        else:
            lines.append(f"{head} | Actual: {r['actual_avg_w']:.0f}W | {_FLAG_SYMBOL[r['compliance']]} ({r['deviation_pct']:+.1f}% outside band)"
                         if r["deviation_pct"] else f"{head} | Actual: {r['actual_avg_w']:.0f}W | ✓ in band")
    lines.append("")
    lines.append(f"  Intervals completed: {result['completed_intervals']}/{result['scored_intervals']} scored")
    if result["systematic_offset_pct"] is not None:
        lines.append(
            f"  ERG scaling: every work interval is a consistent {result['systematic_offset_pct']:+.1f}% outside its band, "
            "which means Zwift's FTP setting differs from the plan FTP. This is NOT an execution error; "
            "scoring corrects for it."
        )
    if result["execution_score"] is not None:
        lines.append(f"  COMPUTED EXECUTION SCORE: {result['execution_score']}/10")
    lines.append("  Deviation is measured from the nearest edge of the target band (inside the band = 0%).")
    return "\n".join(lines) + "\n"
