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
