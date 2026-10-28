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


# Intervals shorter than this are openers/sprints, not the session's work (VO2 sets fall back below).
MIN_WORK_SECONDS = 240
# ...and intervals prescribed well below the session's hard target (a Zone 2 flush) aren't work either.
WORK_INTENSITY_FLOOR = 0.85


def _target(r: Dict[str, Any]) -> float:
    lo, hi = r.get("target_low_w"), r.get("target_high_w")
    return (lo + hi) / 2 if lo and hi else r["actual_avg_w"]


def _merge(segments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """One block from back-to-back hard segments (e.g. 2 min under + 1 min over + 2 min under ...)."""
    if len(segments) == 1:
        return segments[0]
    seconds = sum(r["duration_sec"] for r in segments)

    def weighted(key):
        vals = [(r[key], r["duration_sec"]) for r in segments if r.get(key)]
        return round(sum(v * d for v, d in vals) / sum(d for _, d in vals), 1) if len(vals) == len(segments) else None

    return {"label": "WORK", "name": f"Block of {len(segments)} segments", "duration_sec": seconds,
            "actual_avg_w": round(sum(r["actual_avg_w"] * r["duration_sec"] for r in segments) / seconds, 1),
            "target_low_w": weighted("target_low_w"), "target_high_w": weighted("target_high_w"),
            "interval_index": segments[0].get("interval_index"), "segments": len(segments)}


def _blocks(rows: List[Dict[str, Any]], candidates: List[Dict[str, Any]], floor: float) -> List[Dict[str, Any]]:
    """Runs of consecutive candidate rows prescribed at or above `floor`, each merged into one block."""
    ids = {id(r) for r in candidates}
    blocks, run = [], []
    for r in rows:
        if id(r) in ids and _target(r) >= floor:
            run.append(r)
        else:
            if run:
                blocks.append(_merge(run))
            run = []
    if run:
        blocks.append(_merge(run))
    return blocks


def pick_work(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The blocks that make up a session's work: sustained and at the session's main intensity.

    Intervals are labelled WORK by name, so "Opener" and "Zone 2 Flush" slip in; counting them
    turned a 284 W sweet-spot session into a 246 W "regression". Targets decide instead.

    A plan may cut one block into short pieces (an over-under written as 2 min under / 1 min over, five
    pieces to a block). No piece is "sustained" on its own, so back-to-back hard pieces are merged into one
    block first. Otherwise the only sustained thing left was the easy cool-down, and a 305 W over-under was
    recorded as "1 x 7 min at 194 W".
    """
    candidates = [r for r in rows if r["label"] == "WORK" and r["actual_avg_w"]]
    if not candidates:
        candidates = [r for r in rows if r["label"] not in ("WARMUP", "COOLDOWN") and r["actual_avg_w"]]
    # Highest prescribed intensity first, so a one-minute sprint or opener can't set a floor that hides the real
    # work; the first intensity that yields a sustained block wins.
    for top in sorted({_target(r) for r in candidates}, reverse=True):
        sustained = [b for b in _blocks(rows, candidates, WORK_INTENSITY_FLOOR * top) if b["duration_sec"] >= MIN_WORK_SECONDS]
        if sustained:
            main = max(_target(b) for b in sustained)
            return [b for b in sustained if _target(b) >= WORK_INTENSITY_FLOOR * main]
    return candidates                            # e.g. 30 s VO2max efforts


def work_target_power(work: List[Dict[str, Any]]) -> Optional[float]:
    """Duration-weighted middle of the prescribed power bands over a session's work intervals (None if unprescribed)."""
    pairs = [((r["target_low_w"] + r["target_high_w"]) / 2, r["duration_sec"])
             for r in work if r.get("target_low_w") and r.get("target_high_w")]
    seconds = sum(d for _, d in pairs)
    return round(sum(w * d for w, d in pairs) / seconds, 1) if seconds else None


def work_summary(rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """What a ride's work intervals averaged against what the plan asked for (same selection as the ledger)."""
    work = pick_work([r for r in rows if r.get("actual_avg_w")])
    if not work:
        return None
    seconds = sum(r["duration_sec"] for r in work)
    avg = sum(r["actual_avg_w"] * r["duration_sec"] for r in work) / seconds
    target = work_target_power(work)
    return {"intervals": len(work), "seconds": seconds, "avg_power": round(avg, 1), "target_power": target,
            "diff_w": round(avg - target, 1) if target else None,
            "diff_pct": round((avg - target) / target * 100, 1) if target else None}


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
                "SELECT label, duration_sec, actual_avg_w, target_low_w, target_high_w FROM interval_results "
                "WHERE workout_id = ? ORDER BY interval_index", (w["workout_id"],)
            ).fetchall()
            work = pick_work([dict(r) for r in rows])
            if not work:
                continue
            seconds = sum(r["duration_sec"] for r in work)
            avg_power = sum(r["actual_avg_w"] * r["duration_sec"] for r in work) / seconds
            ftp = w["ftp"]
            pct = avg_power / ftp if ftp else None
            conn.execute(
                "INSERT INTO workout_progression (workout_id, workout_date, archetype, proposed_workout_id,"
                " work_intervals, work_seconds, work_avg_power, normalized_power, pct_ftp, ftp, execution_score,"
                " structure, work_target_power) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (w["workout_id"], w["workout_day"], classify_archetype(w["name"], pct), w["proposed_workout_id"],
                 len(work), seconds, round(avg_power, 1), w["np"], round(pct, 3) if pct else None, ftp,
                 w["execution_score"], describe_structure([r["duration_sec"] for r in work]), work_target_power(work)),
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
                   p.work_avg_power, p.pct_ftp, p.ftp, p.execution_score, p.work_target_power
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
