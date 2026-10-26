"""A session's 'work' is its sustained hard intervals, not openers or a Zone 2 flush."""
from src.utils.progression import pick_work


def iv(name, label, sec, lo, hi, actual):
    return {"label": label, "duration_sec": sec, "target_low_w": lo, "target_high_w": hi, "actual_avg_w": actual, "name": name}


def test_sweet_spot_sharpener_counts_only_the_two_sweet_spot_blocks():
    rows = [
        iv("Warmup", "WARMUP", 900, 140, 205, 170),
        iv("Opener 1", "WORK", 60, 255, 270, 262),
        iv("Easy Spin", "RECOVERY", 60, 150, 165, 155),
        iv("Sweet Spot 1", "WORK", 720, 277, 290, 284),
        iv("Recovery", "RECOVERY", 420, 165, 180, 170),
        iv("Sweet Spot 2", "WORK", 720, 280, 293, 286),
        iv("Zone 2 Flush", "WORK", 900, 195, 210, 203),     # mislabelled WORK by its name
        iv("Cooldown", "COOLDOWN", 420, 120, 150, 130),
    ]
    work = pick_work(rows)
    assert [r["name"] for r in work] == ["Sweet Spot 1", "Sweet Spot 2"]
    avg = sum(r["actual_avg_w"] * r["duration_sec"] for r in work) / sum(r["duration_sec"] for r in work)
    assert round(avg) == 285


def test_short_vo2_efforts_fall_back_to_all_work_labelled_intervals():
    rows = [iv(f"Burst {i}", "WORK", 30, 400, 420, 410) for i in range(6)]
    assert len(pick_work(rows)) == 6


def test_progression_session_without_targets_uses_actual_power():
    rows = [iv("Block 1", "WORK", 1200, None, None, 290), iv("Easy block", "WORK", 600, None, None, 180)]
    assert [r["name"] for r in pick_work(rows)] == ["Block 1"]    # 180 W is under 85% of 290 W


def test_work_target_power_is_the_duration_weighted_middle_of_the_bands():
    from src.utils.progression import work_target_power
    work = [iv("Sweet Spot 1", "WORK", 720, 277, 290, 284), iv("Sweet Spot 2", "WORK", 720, 280, 293, 286)]
    assert work_target_power(work) == 285.0                      # (283.5 + 286.5) / 2
    longer = [iv("A", "WORK", 600, 300, 300, 300), iv("B", "WORK", 1200, 270, 270, 270)]
    assert work_target_power(longer) == 280.0                    # weighted toward the longer block
    assert work_target_power([iv("Block", "WORK", 600, None, None, 290)]) is None
    assert work_target_power([]) is None


def test_work_summary_compares_the_work_intervals_with_the_plan():
    from src.utils.progression import work_summary
    rows = [
        iv("Warmup", "WARMUP", 900, 140, 205, 170),
        iv("Sweet Spot 1", "WORK", 720, 277, 290, 276),
        iv("Recovery", "RECOVERY", 420, 165, 180, 170),
        iv("Sweet Spot 2", "WORK", 720, 280, 293, 276),
        iv("Cooldown", "COOLDOWN", 420, 120, 150, 130),
    ]
    out = work_summary(rows)
    assert (out["intervals"], out["seconds"], out["avg_power"], out["target_power"]) == (2, 1440, 276.0, 285.0)
    assert (out["diff_w"], out["diff_pct"]) == (-9.0, -3.2)


def test_work_summary_without_targets_or_power_is_still_safe():
    from src.utils.progression import work_summary
    out = work_summary([iv("Block", "WORK", 1200, None, None, 290)])
    assert out["avg_power"] == 290.0 and out["target_power"] is None and out["diff_w"] is None
    assert work_summary([]) is None
    assert work_summary([iv("Block", "WORK", 1200, 280, 290, None)]) is None
