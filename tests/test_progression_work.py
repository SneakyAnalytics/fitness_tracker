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


def over_under_plan():
    """The Oct 27 plan: 1-minute openers, then four blocks written as 2 min under / 1 min over pieces."""
    rows = [iv("Progressive Warmup", "WARMUP", 600, 189, 189, 187)]
    for n, (lo, hi, act) in enumerate(((300, 310, 301), (305, 315, 305), (310, 320, 308)), 1):
        rows += [iv(f"Opener {n} - On", "WORK", 60, lo, hi, act), iv(f"Opener {n} - Off", "WORK", 60, 175, 185, 183)]
    rows.append(iv("Settle", "WORK", 180, 170, 180, 176))
    for block in range(1, 5):
        rows += [iv(f"Block {block} - Under", "WORK", 120, 292, 298, 295), iv(f"Block {block} - Over", "WORK", 60, 330, 338, 333),
                 iv(f"Block {block} - Under", "WORK", 120, 292, 298, 296), iv(f"Block {block} - Over", "WORK", 60, 330, 338, 334),
                 iv(f"Block {block} - Under", "WORK", 120, 292, 298, 295)]
        if block < 4:
            rows.append(iv(f"Recovery {block}", "WORK", 300, 165, 178, 172))
    rows.append(iv("Easy Spin Out", "WORK", 420, 190, 200, 194))     # the only interval of 4+ minutes on its own
    rows.append(iv("Cooldown", "COOLDOWN", 300, 120, 150, 130))
    return rows


def test_over_under_cut_into_short_pieces_is_four_eight_minute_blocks_not_the_cooldown():
    from src.utils.progression import describe_structure, work_summary
    work = pick_work(over_under_plan())
    assert [r["duration_sec"] for r in work] == [480, 480, 480, 480]
    assert describe_structure([r["duration_sec"] for r in work]) == "4x8min"
    avg = sum(r["actual_avg_w"] * r["duration_sec"] for r in work) / sum(r["duration_sec"] for r in work)
    assert 304 < avg < 306                                               # ~305 W, in line with the previous over-under (304 W)
    out = work_summary(over_under_plan())
    assert out["intervals"] == 4 and out["seconds"] == 1920 and out["target_power"] and abs(out["diff_pct"]) < 2


def test_a_sprint_above_the_work_cannot_hide_it_and_unders_below_the_floor_still_merge():
    rows = [iv("Sprint", "WORK", 30, 600, 620, 610), iv("Rest", "RECOVERY", 120, 100, 120, 110)] + over_under_plan()[1:]
    assert [r["duration_sec"] for r in pick_work(rows)] == [480, 480, 480, 480]
    soft = []
    for block in range(2):                       # unders at 270 W are under 85% of the 334 W overs, so the overs stand alone...
        soft += [iv("Under", "WORK", 120, 268, 272, 270), iv("Over", "WORK", 60, 330, 338, 334)] * 2 + [iv("Under", "WORK", 120, 268, 272, 270)]
        soft.append(iv("Recovery", "RECOVERY", 300, 150, 160, 155))
    work = pick_work(soft)                       # ...so the pass falls to the unders' level and merges the whole block
    assert [r["duration_sec"] for r in work] == [480, 480]
