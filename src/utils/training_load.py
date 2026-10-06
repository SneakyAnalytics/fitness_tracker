"""Computed training state: load, fitness trend, power curve, FTP, readiness.

Everything here is deterministic. The coach receives these numbers instead of
being asked to infer load and progression from prose.

  CTL  chronic training load: 42-day exponentially weighted daily TSS ("fitness")
  ATL  acute training load:    7-day exponentially weighted daily TSS ("fatigue")
  TSB  training stress balance = CTL - ATL (yesterday's), i.e. "form"
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from statistics import mean, median
from typing import Any, Dict, List, Optional

from src.config import get_db_path

CTL_DAYS = 42
ATL_DAYS = 7
POWER_DURATIONS = {"p5s": 5, "p1m": 60, "p5m": 300, "p20m": 1200, "p60m": 3600}


def _connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _d(value: str) -> date:
    return datetime.strptime(value[:10], "%Y-%m-%d").date()


# ── Load ──────────────────────────────────────────────────────────────────────

def daily_tss(db_path: Optional[str] = None) -> Dict[date, float]:
    """Total TSS per day from completed workouts (TrainingPeaks values)."""
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT workout_day, SUM(CAST(json_extract(workout_data, '$.metrics.actual_tss') AS REAL)) AS tss "
            "FROM workouts GROUP BY workout_day"
        ).fetchall()
    finally:
        conn.close()
    return {_d(r["workout_day"]): float(r["tss"] or 0.0) for r in rows}


def compute_load_series(tss_by_day: Dict[date, float], end: Optional[date] = None) -> List[Dict[str, Any]]:
    """CTL/ATL/TSB for every day from the first workout through `end`."""
    if not tss_by_day:
        return []
    start = min(tss_by_day)
    # Never project into the future: days that haven't happened aren't zero-TSS days.
    end = min(end or date.today(), date.today())
    ctl = atl = 0.0
    series = []
    day = start
    while day <= end:
        tss = tss_by_day.get(day, 0.0)
        tsb = ctl - atl  # form going into the day
        ctl += (tss - ctl) / CTL_DAYS
        atl += (tss - atl) / ATL_DAYS
        series.append({"date": day.isoformat(), "tss": round(tss, 1), "ctl": round(ctl, 1),
                       "atl": round(atl, 1), "tsb": round(tsb, 1)})
        day += timedelta(days=1)
    return series


def refresh_training_load(db_path: Optional[str] = None) -> int:
    """Recompute training_load_daily from scratch (cheap: one row per day)."""
    series = compute_load_series(daily_tss(db_path))
    conn = _connect(db_path)
    try:
        conn.execute("DELETE FROM training_load_daily")
        conn.executemany(
            "INSERT INTO training_load_daily (date, tss, ctl, atl, tsb) VALUES (:date, :tss, :ctl, :atl, :tsb)",
            series,
        )
        conn.commit()
    finally:
        conn.close()
    return len(series)


def get_training_load(start: str, end: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT date, tss, ctl, atl, tsb FROM training_load_daily WHERE date BETWEEN ? AND ? ORDER BY date",
            (start, end),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def weekly_load(db_path: Optional[str] = None, weeks: int = 12, end: Optional[date] = None) -> List[Dict[str, Any]]:
    """Complete Monday-Sunday weeks before `end` (weekly TSS + end-of-week CTL), most recent last."""
    tss_by_day = daily_tss(db_path)
    end = min(end or date.today(), date.today() + timedelta(days=1))
    series = {row["date"]: row for row in compute_load_series(tss_by_day, end)}
    this_monday = end - timedelta(days=end.weekday())
    out = []
    for i in range(weeks, 0, -1):
        monday = this_monday - timedelta(weeks=i)
        days = [monday + timedelta(days=k) for k in range(7)]
        sunday = days[-1].isoformat()
        out.append({
            "week_start": monday.isoformat(),
            "tss": round(sum(tss_by_day.get(d, 0.0) for d in days), 1),
            "ctl_end": series.get(sunday, {}).get("ctl"),
        })
    return out


def load_snapshot(db_path: Optional[str] = None, as_of: Optional[date] = None) -> Dict[str, Any]:
    """Current fitness/fatigue/form plus ramp rate and the year-ago comparison."""
    as_of = min(as_of or date.today(), date.today())
    series = {r["date"]: r for r in compute_load_series(daily_tss(db_path), as_of)}
    if not series:
        return {}

    def at(d: date) -> Optional[Dict[str, Any]]:
        return series.get(d.isoformat())

    now = at(as_of) or series[max(series)]
    week_ago = at(as_of - timedelta(days=7))
    four_weeks_ago = at(as_of - timedelta(days=28))
    year_ago = at(as_of - timedelta(days=365))
    return {
        "as_of": as_of.isoformat(),
        "ctl": now["ctl"], "atl": now["atl"], "tsb": round(now["ctl"] - now["atl"], 1),
        "ctl_ramp_7d": round(now["ctl"] - week_ago["ctl"], 1) if week_ago else None,
        "ctl_ramp_28d_per_week": round((now["ctl"] - four_weeks_ago["ctl"]) / 4, 1) if four_weeks_ago else None,
        "ctl_year_ago": year_ago["ctl"] if year_ago else None,
    }


# ── Power curve ───────────────────────────────────────────────────────────────

def _best_average(samples: List[float], window: int) -> Optional[float]:
    if len(samples) < window:
        return None
    running = sum(samples[:window])
    best = running
    for i in range(window, len(samples)):
        running += samples[i] - samples[i - window]
        if running > best:
            best = running
    return best / window


def ride_power_series(fit_data: Dict[str, Any]) -> List[float]:
    """1 Hz power with coasting kept as zeros where possible."""
    ts = fit_data.get("time_series") or {}
    power = ts.get("power") or []
    if power and len(power) == len(ts.get("timestamps") or []):
        return [float(p or 0) for p in power]
    return [float(p or 0) for p in (fit_data.get("power_metrics") or {}).get("power_series") or []]


def refresh_ride_power_bests(db_path: Optional[str] = None, only_missing: bool = True) -> int:
    conn = _connect(db_path)
    try:
        sql = "SELECT f.id, f.workout_day, f.fit_data FROM fit_files f"
        if only_missing:
            sql += " LEFT JOIN ride_power_bests b ON b.fit_file_id = f.id WHERE b.fit_file_id IS NULL"
        rows = conn.execute(sql).fetchall()
        count = 0
        for row in rows:
            try:
                fit = (json.loads(row["fit_data"]) if row["fit_data"] else None) or {}
            except ValueError:
                continue
            samples = ride_power_series(fit)
            if len(samples) < 60:
                continue
            bests = {k: _best_average(samples, w) for k, w in POWER_DURATIONS.items()}
            conn.execute(
                "INSERT OR REPLACE INTO ride_power_bests (fit_file_id, ride_date, p5s, p1m, p5m, p20m, p60m) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (row["id"], row["workout_day"], *[round(bests[k], 1) if bests[k] else None for k in POWER_DURATIONS]),
            )
            count += 1
        conn.commit()
        return count
    finally:
        conn.close()


def power_curve(start: str, end: str, db_path: Optional[str] = None) -> Dict[str, Optional[float]]:
    """Best power at each standard duration over a date window."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT MAX(p5s) p5s, MAX(p1m) p1m, MAX(p5m) p5m, MAX(p20m) p20m, MAX(p60m) p60m, COUNT(*) rides "
            "FROM ride_power_bests WHERE ride_date BETWEEN ? AND ?", (start, end)
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else {}


def compare_power_curves(window_days: int = 90, years_back: int = 1, db_path: Optional[str] = None,
                         as_of: Optional[date] = None) -> Dict[str, Any]:
    """Last N days vs the same N days a year earlier: "am I fitter than last year?"."""
    as_of = as_of or date.today()
    recent = power_curve((as_of - timedelta(days=window_days)).isoformat(), as_of.isoformat(), db_path)
    then_end = as_of - timedelta(days=365 * years_back)
    prior = power_curve((then_end - timedelta(days=window_days)).isoformat(), then_end.isoformat(), db_path)
    delta = {}
    for key in POWER_DURATIONS:
        a, b = recent.get(key), prior.get(key)
        delta[key] = round((a - b) / b * 100, 1) if a and b else None
    return {"window_days": window_days, "recent": recent, "year_ago": prior, "change_pct": delta}


# ── FTP ───────────────────────────────────────────────────────────────────────

def estimate_ftp(db_path: Optional[str] = None, window_days: int = 90,
                 as_of: Optional[date] = None) -> Dict[str, Any]:
    """FTP estimate from recent best efforts: max(95% of 20-min, 60-min).

    ERG workouts cap power at the prescription, so structured-only periods
    under-estimate; the result is a floor, flagged for the athlete to confirm.
    """
    as_of = as_of or date.today()
    curve = power_curve((as_of - timedelta(days=window_days)).isoformat(), as_of.isoformat(), db_path)
    candidates = []
    if curve.get("p20m"):
        candidates.append(("95% of best 20-min", curve["p20m"] * 0.95))
    if curve.get("p60m"):
        candidates.append(("best 60-min", curve["p60m"]))
    if not candidates:
        return {"estimate": None, "basis": None, "window_days": window_days}
    basis, value = max(candidates, key=lambda c: c[1])
    return {"estimate": round(value), "basis": basis, "window_days": window_days,
            "p20m": curve.get("p20m"), "p60m": curve.get("p60m")}


def ftp_check(current_ftp: Optional[float], db_path: Optional[str] = None) -> Dict[str, Any]:
    est = estimate_ftp(db_path)
    result = {"current_ftp": current_ftp, **est, "flag": None}
    if current_ftp and est.get("estimate"):
        diff = (est["estimate"] - current_ftp) / current_ftp * 100
        result["diff_pct"] = round(diff, 1)
        if diff >= 3:
            result["flag"] = "recent efforts suggest FTP is higher than the setting — consider a test or raising it"
        elif diff <= -8:
            result["flag"] = ("recent best efforts are well below the FTP setting; that is expected if riding was "
                              "mostly ERG at sub-threshold targets, otherwise consider retesting")
    return result


# ── Readiness ─────────────────────────────────────────────────────────────────

READINESS_METRICS = {"HRV": "hrv", "Pulse": "resting_hr", "Sleep Hours": "sleep_hours", "Body Battery": "body_battery"}


def _metric_value(metric_data: str, metric_type: str) -> Optional[float]:
    try:
        data = json.loads(metric_data)
    except (TypeError, ValueError):
        return None
    summary = data.get("summary") or {}
    if metric_type == "Body Battery":
        return summary.get("max")  # morning charge level
    return summary.get("avg")


def readiness(as_of: Optional[date] = None, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Last-7-day biometrics vs a 60-day baseline, with plain-language flags."""
    as_of = as_of or date.today()
    start = (as_of - timedelta(days=67)).isoformat()
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            f"SELECT date, metric_type, metric_data FROM daily_metrics WHERE date BETWEEN ? AND ? "
            f"AND metric_type IN ({','.join('?' * len(READINESS_METRICS))})",
            (start, as_of.isoformat(), *READINESS_METRICS),
        ).fetchall()
    finally:
        conn.close()

    by_metric: Dict[str, Dict[str, List[float]]] = {}
    recent_cut = (as_of - timedelta(days=7)).isoformat()
    for r in rows:
        value = _metric_value(r["metric_data"], r["metric_type"])
        if value is None:
            continue
        key = READINESS_METRICS[r["metric_type"]]
        bucket = "recent" if r["date"][:10] > recent_cut else "baseline"
        by_metric.setdefault(key, {"recent": [], "baseline": []})[bucket].append(value)

    out: Dict[str, Any] = {"as_of": as_of.isoformat(), "metrics": {}, "flags": []}
    for key, vals in by_metric.items():
        if not vals["recent"]:
            continue
        r_avg = mean(vals["recent"])
        b_avg = median(vals["baseline"]) if vals["baseline"] else None
        change = round((r_avg - b_avg) / b_avg * 100, 1) if b_avg else None
        out["metrics"][key] = {"last7": round(r_avg, 1), "baseline60": round(b_avg, 1) if b_avg else None,
                               "change_pct": change}
    m = out["metrics"]
    if m.get("hrv", {}).get("change_pct") is not None and m["hrv"]["change_pct"] <= -10:
        out["flags"].append("HRV is suppressed vs baseline (possible accumulated fatigue, illness or stress)")
    if m.get("resting_hr", {}).get("change_pct") is not None and m["resting_hr"]["change_pct"] >= 5:
        out["flags"].append("Resting HR is elevated vs baseline")
    if m.get("sleep_hours", {}).get("last7") is not None and m["sleep_hours"]["last7"] < 7:
        out["flags"].append(f"Averaging {m['sleep_hours']['last7']}h sleep this week (sleep debt)")
    if m.get("body_battery", {}).get("last7") is not None and m["body_battery"]["last7"] < 50:
        out["flags"].append("Body Battery is not recharging overnight (low morning peaks)")
    return out


def body_metrics(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Most recent scale reading (needed for fueling and W/kg)."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT date, metric_data FROM daily_metrics WHERE metric_type = 'Weight Pounds' "
            "ORDER BY date DESC LIMIT 1").fetchone()
    finally:
        conn.close()
    if not row:
        return {}
    lb = _metric_value(row["metric_data"], "Weight Pounds")
    return {"date": row["date"][:10], "weight_lb": round(lb, 1), "weight_kg": round(lb * 0.4536, 1)} if lb else {}


def refresh_all(db_path: Optional[str] = None) -> Dict[str, int]:
    """Refresh every derived table. Safe to run after each sync."""
    from src.utils.progression import refresh_progression
    from src.utils import zwift_ftp
    from src.storage.workout_matching import heal_name_only_matches
    heal_name_only_matches(db_path or get_db_path())
    result = {
        "load_days": refresh_training_load(db_path),
        "ride_power_bests": refresh_ride_power_bests(db_path),
        "progression_rows": refresh_progression(db_path),
        "zwift_ftp_observations": zwift_ftp.refresh_observations(db_path),
    }
    change = zwift_ftp.sync_settings_ftp(db_path)
    if change:
        result["ftp_change"] = change
    return result
