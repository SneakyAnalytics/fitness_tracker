from src.utils.erg_execution import (
    compute_execution,
    deviation_pct,
    format_execution_text,
    resolve_target,
)

FTP = 300

PLAN = {
    "intervals": [
        {"name": "Warmup", "duration": 300, "powerTarget": {"type": "range", "min": 150, "max": 180, "unit": "watts"}},
        {"name": "Threshold 1", "duration": 600, "powerTarget": {"type": "range", "min": 280, "max": 295, "unit": "watts"}},
        {"name": "Recovery", "duration": 300, "powerTarget": {"type": "range", "min": 150, "max": 170, "unit": "watts"}},
        {"name": "Threshold 2", "duration": 600, "powerTarget": {"type": "range", "min": 280, "max": 295, "unit": "watts"}},
        {"name": "Cooldown", "duration": 300, "powerTarget": {"type": "range", "min": 140, "max": 170, "unit": "watts"}},
    ]
}


def laps_for(powers, durations=(300, 600, 300, 600, 300)):
    return [{"total_elapsed_time": d - 1, "avg_power": p} for d, p in zip(durations, powers)]


def test_deviation_is_zero_inside_band_and_measured_from_nearest_edge():
    assert deviation_pct(285, 280, 295) == 0.0
    assert round(deviation_pct(266, 280, 295), 1) == -5.0
    assert round(deviation_pct(300, 280, 295), 1) == 1.7


def test_percent_ftp_range_is_converted_to_watts():
    lo, hi, _ = resolve_target({"type": "range", "min": 88, "max": 93, "unit": "percent_ftp"}, 300)
    assert (lo, hi) == (264.0, 279.0)


def test_perfect_ride_with_trailing_zwift_lap_scores_ten():
    laps = laps_for([160, 282, 160, 282, 150]) + [{"total_elapsed_time": 9, "avg_power": 140}]
    result = compute_execution(PLAN, {"laps": laps}, FTP)
    assert result["alignment"] == "laps"
    assert result["execution_score"] == 10.0
    assert result["systematic_offset_pct"] is None


def test_leading_extra_lap_does_not_shift_every_interval():
    # Pre-workout free ride recorded as its own lap: must be skipped, not paired
    # with the warmup (which would compare each interval to the previous one).
    laps = [{"total_elapsed_time": 95, "avg_power": 120}] + laps_for([160, 282, 160, 282, 150])
    result = compute_execution(PLAN, {"laps": laps}, FTP)
    assert result["alignment"] == "laps"
    assert [r["actual_avg_w"] for r in result["intervals"]] == [160, 282, 160, 282, 150]
    assert result["execution_score"] == 10.0


def test_laps_with_wrong_durations_are_not_trusted():
    laps = [{"total_elapsed_time": 60, "avg_power": 200}] * 5  # auto-laps every minute
    series = [160] * 300 + [282] * 600 + [160] * 300 + [282] * 600 + [150] * 300
    result = compute_execution(PLAN, {"laps": laps, "time_series": {"power": series}}, FTP)
    assert result["alignment"] == "time_series"
    assert result["execution_score"] == 10.0


def test_time_series_alignment_skips_pre_ride_spin():
    series = [100] * 90 + [160] * 300 + [282] * 600 + [160] * 300 + [282] * 600 + [150] * 300
    result = compute_execution(PLAN, {"time_series": {"power": series}}, FTP)
    assert result["alignment"] == "time_series"
    assert abs(result["time_offset_sec"] - 90) <= 5
    assert result["execution_score"] == 10.0


def test_consistent_offset_is_flagged_as_zwift_ftp_mismatch_not_bad_execution():
    # Every work interval 6% under the floor in ERG: Zwift FTP is lower than plan FTP.
    laps = laps_for([150, 263, 150, 263, 140])
    result = compute_execution(PLAN, {"laps": laps}, FTP)
    assert result["systematic_offset_pct"] is not None
    assert result["systematic_offset_pct"] < -5
    assert result["execution_score"] == 10.0
    assert "NOT an execution error" in format_execution_text(result)


def test_genuinely_missed_targets_score_low():
    laps = laps_for([160, 282, 160, 230, 150])  # faded to ~18% under on the second interval
    result = compute_execution(PLAN, {"laps": laps}, FTP)
    assert result["systematic_offset_pct"] is None
    assert result["intervals"][3]["compliance"] == "low"
    assert result["execution_score"] == 6.5  # one perfect, one at partial credit


def test_cut_short_session_scores_missing_intervals_as_zero():
    series = [160] * 300 + [282] * 600 + [160] * 300  # stopped before the second interval
    result = compute_execution(PLAN, {"time_series": {"power": series}}, FTP)
    assert result["completed_intervals"] == 1
    assert result["execution_score"] == 5.0


def test_misaligned_zero_filtered_series_is_refused():
    # Parser drops zero samples from time_series.power; if lengths diverge from
    # timestamps the series no longer lines up with time, so don't guess.
    data = {"time_series": {"power": [200] * 100, "timestamps": ["t"] * 120}}
    assert compute_execution(PLAN, data, FTP) is None


def test_ride_without_power_meter_is_not_scored_as_zero():
    laps = [{"total_elapsed_time": d - 1, "avg_power": None} for d in (300, 600, 300, 600, 300)]
    assert compute_execution(PLAN, {"laps": laps}, FTP) is None
