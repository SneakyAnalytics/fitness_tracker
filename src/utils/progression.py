"""Progression ledger: what was actually done in each kind of key workout.

For every matched, structured ride we record the archetype (threshold, VO2max,
sweet spot...) and the work actually performed. The coach can then see
"Threshold: 2x15 @ 282W -> 2x18 @ 288W -> 2x18 @ 291W" and prescribe the next
step, instead of re-inventing each week from scratch.
"""
from __future__ import annotations

import sqlite3
from collections import Counter
from typing import Any, Dict, List, Optional

from src.config import get_db_path

ARCHETYPES = ("vo2max", "over_under", "threshold", "sweet_spot", "tempo", "race",
              "endurance", "recovery", "other")

# Checked in order; first match wins.
_NAME_RULES = [
    ("recovery", ("active recovery", "recovery spin", "flush", "easy spin", "recovery ride")),
    ("vo2max", ("vo2", "vo₂")),
    ("over_under", ("over-under", "over/under", "over under", "overs/unders", "over-unders")),
    ("sweet_spot", ("sweet spot", "sweetspot")),
    ("threshold", ("threshold", "ftp interval", "pyramid")),
    ("tempo", ("tempo",)),
    ("race", ("race", "zrl", "crit")),
    ("endurance", ("endurance", "zone 2", "z2", "aerobic", "long ride", "base")),
]


def classify_archetype(name: str, pct_ftp: Optional[float] = None) -> str:
    lowered = (name or "").lower()
    for archetype, words in _NAME_RULES:
        if any(w in lowered for w in words):
            return archetype
    if pct_ftp is None:
        return "other"
    if pct_ftp >= 1.05:
        return "vo2max"
    if pct_ftp >= 0.95:
        return "threshold"
    if pct_ftp >= 0.88:
        return "sweet_spot"
    if pct_ftp >= 0.76:
        return "tempo"
    if pct_ftp >= 0.56:
        return "endurance"
    return "recovery"


def describe_structure(durations: List[int]) -> str:
    """e.g. [1200, 1200, 1200] -> '3x20min'; mixed -> '4x8min + 1x5min'."""
    if not durations:
        return ""
    counts = Counter(durations)
    parts = []
    for dur, n in sorted(counts.items(), key=lambda kv: (-kv[1], -kv[0])):
        mins = dur / 60
        label = f"{mins:.0f}min" if mins == int(mins) else f"{mins:.1f}min"
        parts.append(f"{n}x{label}")
    return " + ".join(parts)


def refresh_progression(db_path: Optional[str] = None) -> int:
    """Rebuild workout_progression from interval_results (deterministic, cheap)."""
    conn = sqlite3.connect(db_path or get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        workouts = conn.execute("""
            SELECT DISTINCT ir.workout_id, w.workout_day, ir.proposed_workout_id, pw.name,
                   COALESCE(pw.prescribed_ftp, wp.ftp) AS ftp, wa.execution_score,
                   json_extract(f.fit_data, '$.power_metrics.normalized_power') AS np
            FROM interval_results ir
            JOIN workouts w ON w.id = ir.workout_id
            LEFT JOIN proposed_workouts pw ON pw.id = ir.proposed_workout_id
            LEFT JOIN daily_plans dp ON dp.id = pw.dailyPlanId
            LEFT JOIN weekly_plans wp ON wp.weekNumber = dp.weekNumber
            LEFT JOIN workout_analyses wa ON wa.workout_id = ir.workout_id
            LEFT JOIN fit_files f ON f.id = w.fit_file_id
        """).fetchall()
        conn.execute("DELETE FROM workout_progression")
        for w in workouts:
            rows = conn.execute(
                "SELECT label, duration_sec, actual_avg_w FROM interval_results "
                "WHERE workout_id = ? ORDER BY interval_index", (w["workout_id"],)
            ).fetchall()
            work = [r for r in rows if r["label"] == "WORK" and r["actual_avg_w"]]
            if not work:
                work = [r for r in rows if r["label"] not in ("WARMUP", "COOLDOWN") and r["actual_avg_w"]]
            if not work:
                continue
            seconds = sum(r["duration_sec"] for r in work)
            avg_power = sum(r["actual_avg_w"] * r["duration_sec"] for r in work) / seconds
            ftp = w["ftp"]
            pct = avg_power / ftp if ftp else None
            conn.execute(
                "INSERT INTO workout_progression (workout_id, workout_date, archetype, proposed_workout_id,"
                " work_intervals, work_seconds, work_avg_power, normalized_power, pct_ftp, ftp, execution_score,"
                " structure) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (w["workout_id"], w["workout_day"], classify_archetype(w["name"], pct), w["proposed_workout_id"],
                 len(work), seconds, round(avg_power, 1), w["np"], round(pct, 3) if pct else None, ftp,
                 w["execution_score"], describe_structure([r["duration_sec"] for r in work])),
            )
        conn.commit()
        return conn.execute("SELECT COUNT(*) FROM workout_progression").fetchone()[0]
    finally:
        conn.close()


def get_progression(archetype: Optional[str] = None, limit: int = 6,
                    db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Most recent sessions of an archetype (or all), oldest first."""
    conn = sqlite3.connect(db_path or get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        where, params = ("WHERE p.archetype = ?", [archetype]) if archetype else ("", [])
        rows = conn.execute(f"""
            SELECT p.workout_date, p.archetype, pw.name, p.structure, p.work_intervals, p.work_seconds,
                   p.work_avg_power, p.pct_ftp, p.ftp, p.execution_score
            FROM workout_progression p LEFT JOIN proposed_workouts pw ON pw.id = p.proposed_workout_id
            {where} ORDER BY p.workout_date DESC LIMIT ?
        """, (*params, limit)).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in reversed(rows)]


def progression_summary(db_path: Optional[str] = None, per_type: int = 4,
                        types=("threshold", "sweet_spot", "over_under", "vo2max", "tempo", "endurance")) -> str:
    """Compact text block for prompts: recent trajectory per key archetype."""
    lines = []
    for archetype in types:
        sessions = get_progression(archetype, per_type, db_path)
        if not sessions:
            continue
        steps = []
        for s in sessions:
            pct = f" ({s['pct_ftp'] * 100:.0f}% FTP)" if s["pct_ftp"] else ""
            score = f", exec {s['execution_score']:.0f}/10" if s["execution_score"] is not None else ""
            steps.append(f"{s['workout_date']} {s['structure']} @ {s['work_avg_power']:.0f}W{pct}"
                         f" = {s['work_seconds'] // 60}min work{score}")
        lines.append(f"- **{archetype.replace('_', ' ').title()}:** " + " → ".join(steps))
    return "\n".join(lines)
