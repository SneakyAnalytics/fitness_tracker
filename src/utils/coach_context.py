"""The computed training state handed to the coach at the start of every session."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from src.storage import goals as goals_store
from src.utils import training_load, zwift_ftp
from src.utils.periodization import WeekTarget, plan_next_week
from src.utils.progression import progression_summary


def build_training_state(week_start_date: str, current_ftp: Optional[float] = None,
                         db_path: Optional[str] = None, refresh: bool = True) -> Tuple[str, WeekTarget]:
    """Text block + next-week target for the week after `week_start_date`.

    Derived tables are refreshed first (unless refresh=False) so the coach never
    reasons from stale data.
    """
    if refresh:
        training_load.refresh_all(db_path)
    this_monday = datetime.strptime(week_start_date[:10], "%Y-%m-%d").date()
    next_monday = this_monday + timedelta(days=7)
    as_of = min(date.today(), next_monday - timedelta(days=1))

    snapshot = training_load.load_snapshot(db_path, as_of=as_of)
    readiness = training_load.readiness(as_of, db_path)
    goals = goals_store.list_goals(db_path=db_path)
    target = plan_next_week(next_monday, goals=goals, readiness=readiness, db_path=db_path)
    trajectory = progression_summary(db_path)

    today = date.today()
    lines = [f"# Computed Training State (from the data — trust these numbers)",
             f"**Today is {today:%A %Y-%m-%d}.** Anything dated after today hasn't happened yet.", ""]
    body = training_load.body_metrics(db_path)
    if body:
        wkg = f"; {current_ftp / body['weight_kg']:.2f} W/kg at FTP {current_ftp}W" if current_ftp else ""
        lines.append(f"**Body weight:** {body['weight_lb']} lb ({body['weight_kg']} kg) as of {body['date']}{wkg}. "
                     "Use this for fueling and W/kg; don't assume a weight.")
    if snapshot:
        year = (f"; a year ago CTL was {snapshot['ctl_year_ago']:.0f}"
                if snapshot.get("ctl_year_ago") is not None else "")
        ramp = (f", ramping {snapshot['ctl_ramp_28d_per_week']:+.1f} CTL/week over the last 4 weeks"
                if snapshot.get("ctl_ramp_28d_per_week") is not None else "")
        lines.append(f"**Fitness/fatigue/form:** CTL {snapshot['ctl']:.0f} · ATL {snapshot['atl']:.0f} · "
                     f"TSB {snapshot['tsb']:+.0f}{ramp}{year}.")
    lines += ["", target.prompt_block(), ""]
    lines.append("## Key-session progression (oldest → newest; work intervals only)")
    lines.append(trajectory or "_No matched structured sessions yet._")
    lines.append("")
    lines.append("## Readiness (last 7 days vs 60-day baseline)")
    metrics = readiness.get("metrics", {})
    if metrics:
        lines.append(", ".join(f"{k.replace('_', ' ')} {v['last7']}"
                               + (f" ({v['change_pct']:+.0f}%)" if v.get("change_pct") is not None else "")
                               for k, v in metrics.items()))
    lines.append("Flags: " + ("; ".join(readiness["flags"]) if readiness.get("flags") else "none"))
    lines.append("")
    zftp = zwift_ftp.current(db_path)
    if zftp.get("ftp"):
        lines.append("## FTP (Zwift's — the app follows it automatically)")
        lines.append(f"Zwift FTP {zftp['ftp']}W, read from Zwift's ERG targets on {zftp['observed']}; "
                     f"last changed {zftp['changed_on']}"
                     + (f", last ramp test/race {zftp['last_test_or_race']}" if zftp.get("last_test_or_race") else "")
                     + f" ({zftp['weeks_since_change']} weeks ago). Zwift scales every .zwo by this number, "
                     "so plan watts at this FTP. Only a Zwift ramp/FTP test or a Zwift race changes it.")
        if zftp.get("test_due"):
            lines.append(
                f"**FTP test due ({zftp['weeks_since_change']} weeks without one).** Put a Zwift Ramp Test (or a "
                "Zwift race) in next week's plan on a fresh day — the last day or two of a recovery week, or day "
                "1-2 of a build week. Make it a bike workout named \"Zwift Ramp Test\" with no intervals and a note "
                "to use Zwift's built-in Ramp Test, so Zwift updates its FTP. Tell the athlete why.")
        lines.append("")
    stale = [g for g in goals if g.get("stale")]
    if stale:
        lines.append("\n## Goals needing attention\n" + "\n".join(
            f"- #{g['id']} \"{g['description']}\" is still active but its date ({g['target_date']}) has passed — "
            "ask whether it happened and update it." for g in stale))
    return "\n".join(lines), target


TOOL_INSTRUCTIONS = """## Your tools

You can look things up. Use them instead of asking the athlete to repeat themselves:
- Before asking about schedule, travel, injuries, equipment, preferences or events,
  call `search_prior_conversations` — they may have told you in an earlier week.
- Before prescribing a key session, call `get_progression` for that workout type and
  make next week's version a deliberate step (more time-in-zone, a few more watts,
  or one more interval) unless readiness or a recovery week says otherwise.
- When the athlete mentions a new goal or event, call `save_goal` right away; when they
  report finishing or dropping one, call `update_goal`.
- Use `compare_to_period` when asked whether they're fitter than before.
Keep tool use purposeful: a few well-chosen lookups, not every tool every turn."""


PROGRESSION_RULES = """## Progression rules (replace "maximize variety")

- Pick 2-3 key sessions for the week that serve the current block and the next
  priority event. Repeating a workout TYPE week to week is how it progresses — vary
  the structure within a type, not the type itself.
- Each key session must progress from the most recent session of that type in the
  progression table: e.g. +5-10% time-in-zone, +2-3% power, or one more interval.
  If the last one scored below 7/10 execution, repeat it rather than progress.
- Recovery weeks keep one short quality session at the previous level and cut volume.
- Stay inside the computed weekly TSS band."""
