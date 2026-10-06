"""Next week's load target, derived rather than invented.

The LLM used to pick weekly TSS from scratch each week (and, through a data
bug, was anchored to a hardcoded 400-500). Here the band comes from current
fitness, a bounded CTL ramp, a 3-build : 1-recovery cadence, and tapers into
dated goal events. The plan generator works inside this band and the validator
enforces it.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from src.utils.training_load import CTL_DAYS, load_snapshot, weekly_load

# Weekly CTL gain for a build week. 2-5/week is sustainable for most amateurs;
# start conservative and let compliance + readiness earn the top of the band.
BUILD_RAMP_LOW = 2.0
BUILD_RAMP_HIGH = 4.0
# Never jump more than this above the recent 3-week average in one week.
MAX_WEEK_OVER_WEEK = 1.12
DELOAD_FRACTION = (0.60, 0.70)
TAPER_FRACTION = (0.60, 0.75)      # 8-14 days out from an A event
RACE_WEEK_FRACTION = (0.40, 0.55)  # event within 7 days
BUILD_WEEKS_BEFORE_DELOAD = 3
# A week this far below the preceding weeks counts as a recovery week.
RECOVERY_WEEK_THRESHOLD = 0.80
# Tolerance when validating a generated plan against the band.
VALIDATION_TOLERANCE = 0.10

_DECAY_7 = (1 - 1 / CTL_DAYS) ** 7


def weekly_tss_for_ctl_change(ctl: float, delta: float) -> float:
    """Weekly TSS (spread evenly) that moves CTL by `delta` over 7 days."""
    daily = (ctl + delta - ctl * _DECAY_7) / (1 - _DECAY_7)
    return max(0.0, daily * 7)


@dataclass
class WeekTarget:
    week_start: str
    week_type: str  # build | recovery | taper | race
    tss_min: int
    tss_max: int
    ctl_now: float
    atl_now: float
    tsb_now: float
    build_weeks_in_row: int
    recent_weeks: List[Dict[str, Any]]
    event: Optional[Dict[str, Any]] = None
    readiness_flags: List[str] = field(default_factory=list)
    rationale: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def prompt_block(self) -> str:
        lines = [
            "# Next Week's Load Target (computed — work within this)",
            f"- **Week type:** {self.week_type.upper()}",
            f"- **Weekly TSS band:** {self.tss_min}-{self.tss_max}",
            f"- **Current fitness (CTL):** {self.ctl_now:.0f} · fatigue (ATL) {self.atl_now:.0f} · form (TSB) {self.tsb_now:+.0f}",
            f"- **Consecutive build weeks:** {self.build_weeks_in_row}",
            "- **Recent weeks:** " + ", ".join(f"{w['week_start']} {w['tss']:.0f}" for w in self.recent_weeks),
        ]
        if self.event:
            lines.append(f"- **Next priority event:** {self.event['description']} in {self.event['days_out']} days")
        lines.append("- **Why:** " + " ".join(self.rationale))
        if self.readiness_flags:
            lines.append("- **Readiness flags:** " + "; ".join(self.readiness_flags)
                         + " → if the athlete confirms fatigue, plan at the bottom of the band or call a recovery week")
        lines.append(f"- Set the plan's plannedTSS min/max inside {self.tss_min}-{self.tss_max}. "
                     "Plans outside the band are rejected.")
        return "\n".join(lines)


def _count_build_weeks(weeks: List[Dict[str, Any]]) -> int:
    """Consecutive non-recovery weeks ending with the most recent one."""
    count = 0
    for i in range(len(weeks) - 1, -1, -1):
        prior = [w["tss"] for w in weeks[max(0, i - 3):i] if w["tss"] > 0]
        if prior and weeks[i]["tss"] < RECOVERY_WEEK_THRESHOLD * (sum(prior) / len(prior)):
            break
        count += 1
    return count


def _next_event(goals: List[Dict[str, Any]], week_start: date) -> Optional[Dict[str, Any]]:
    upcoming = []
    for g in goals or []:
        if g.get("status", "active") != "active" or not g.get("target_date"):
            continue
        if (g.get("priority") or 5) > 2:  # only A/B priority events drive tapers
            continue
        try:
            target = datetime.strptime(str(g["target_date"])[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        days_out = (target - week_start).days
        if 0 <= days_out <= 21:
            upcoming.append({"description": g.get("description", "event"), "target_date": target.isoformat(),
                             "days_out": days_out, "priority": g.get("priority")})
    return min(upcoming, key=lambda e: e["days_out"]) if upcoming else None


def plan_next_week(week_start: Optional[date] = None, goals: Optional[List[Dict[str, Any]]] = None,
                   readiness: Optional[Dict[str, Any]] = None, db_path: Optional[str] = None) -> WeekTarget:
    today = date.today()
    week_start = week_start or (today + timedelta(days=7 - today.weekday()))
    as_of = week_start - timedelta(days=1)
    snap = load_snapshot(db_path, as_of=as_of)
    weeks = weekly_load(db_path, weeks=6, end=as_of + timedelta(days=1))
    recent = [w for w in weeks if w["tss"] > 0][-3:] or weeks[-3:]
    recent_avg = sum(w["tss"] for w in recent) / len(recent) if recent else 0.0
    ctl = snap.get("ctl", 0.0)
    build_weeks = _count_build_weeks(weeks)
    event = _next_event(goals or [], week_start)
    flags = list((readiness or {}).get("flags") or [])
    rationale: List[str] = []

    if event and event["days_out"] <= 7:
        week_type = "race"
        lo, hi = (recent_avg * f for f in RACE_WEEK_FRACTION)
        rationale.append(f"{event['description']} is {event['days_out']} days out: race week, keep intensity, cut volume.")
    elif event and event["days_out"] <= 14:
        week_type = "taper"
        lo, hi = (recent_avg * f for f in TAPER_FRACTION)
        rationale.append(f"{event['description']} is {event['days_out']} days out: taper to arrive fresh.")
    elif build_weeks >= BUILD_WEEKS_BEFORE_DELOAD:
        week_type = "recovery"
        lo, hi = (recent_avg * f for f in DELOAD_FRACTION)
        rationale.append(f"{build_weeks} build weeks in a row: absorb the training with a recovery week "
                         "(keep one short quality session).")
    else:
        week_type = "build"
        lo = weekly_tss_for_ctl_change(ctl, BUILD_RAMP_LOW)
        hi = weekly_tss_for_ctl_change(ctl, BUILD_RAMP_HIGH)
        cap = recent_avg * MAX_WEEK_OVER_WEEK if recent_avg else hi
        if hi > cap:
            hi = cap
            rationale.append(f"Ramp capped at +{(MAX_WEEK_OVER_WEEK - 1) * 100:.0f}% over the recent average.")
        if lo > hi:
            lo = hi * 0.92
        if lo < recent_avg * 0.95 and recent_avg:
            lo = min(recent_avg * 0.95, hi)
        rationale.insert(0, f"Build week {build_weeks + 1} of {BUILD_WEEKS_BEFORE_DELOAD}: "
                            f"raise fitness by ~{BUILD_RAMP_LOW:.0f}-{BUILD_RAMP_HIGH:.0f} CTL from {ctl:.0f}.")
        if flags:
            hi = lo + (hi - lo) * 0.5
            rationale.append("Readiness flags present: top of band trimmed.")

    return WeekTarget(
        week_start=week_start.isoformat(),
        week_type=week_type,
        tss_min=int(round(lo / 5) * 5),
        tss_max=int(round(hi / 5) * 5),
        ctl_now=ctl,
        atl_now=snap.get("atl", 0.0),
        tsb_now=snap.get("tsb", 0.0),
        build_weeks_in_row=build_weeks,
        recent_weeks=[{"week_start": w["week_start"], "tss": w["tss"]} for w in weeks[-4:]],
        event=event,
        readiness_flags=flags,
        rationale=rationale,
    )


def validate_plan_tss(plan_tss_min: Optional[float], plan_tss_max: Optional[float],
                      target: Dict[str, Any]) -> Optional[str]:
    """Error message if a generated plan's weekly TSS falls outside the band."""
    if plan_tss_min is None or plan_tss_max is None or not target:
        return None
    lo = target["tss_min"] * (1 - VALIDATION_TOLERANCE)
    hi = target["tss_max"] * (1 + VALIDATION_TOLERANCE)
    mid = (plan_tss_min + plan_tss_max) / 2
    if lo <= mid <= hi:
        return None
    return (f"Planned weekly TSS {plan_tss_min:.0f}-{plan_tss_max:.0f} is outside the computed "
            f"{target['week_type']} band {target['tss_min']}-{target['tss_max']}")
