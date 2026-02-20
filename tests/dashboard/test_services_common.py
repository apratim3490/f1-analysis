"""Tests for shared/services/common.py — pure functions."""

from __future__ import annotations

import pytest

from shared.services.common import (
    assign_driver_colors,
    compute_avg_lap,
    compute_ideal_lap,
    compute_session_best,
    compute_session_median,
    compute_speed_stats,
    filter_clean_laps,
    filter_valid_laps,
    normalize_team_color,
    split_clean_and_pit_out,
)


class TestFilterValidLaps:
    def test_filters_none_duration(self, sample_laps):
        result = filter_valid_laps(sample_laps)
        assert all(lap["lap_duration"] is not None for lap in result)
        # lap 6 has None duration
        assert len(result) == 9

    def test_empty_list(self):
        assert filter_valid_laps([]) == []

    def test_all_none(self, make_lap):
        laps = [make_lap(1, lap_duration=None), make_lap(2, lap_duration=None)]
        assert filter_valid_laps(laps) == []


class TestFilterCleanLaps:
    def test_excludes_pit_out_and_none(self, sample_laps):
        result = filter_clean_laps(sample_laps)
        assert all(not lap.get("is_pit_out_lap") for lap in result)
        assert all(lap["lap_duration"] is not None for lap in result)
        # 10 laps - 1 pit-out - 1 None = 8
        assert len(result) == 8

    def test_empty_list(self):
        assert filter_clean_laps([]) == []


class TestSplitCleanAndPitOut:
    def test_splits_correctly(self, sample_laps):
        valid = filter_valid_laps(sample_laps)
        clean, pit_out = split_clean_and_pit_out(valid)
        assert len(pit_out) == 1
        assert pit_out[0]["lap_number"] == 1
        assert len(clean) == 8

    def test_no_pit_out(self, make_lap):
        laps = [make_lap(1), make_lap(2)]
        clean, pit_out = split_clean_and_pit_out(laps)
        assert len(clean) == 2
        assert len(pit_out) == 0


class TestComputeSessionBest:
    def test_returns_min(self, sample_all_laps):
        result = compute_session_best(sample_all_laps)
        assert result == 90.5  # driver 2, lap 3

    def test_empty(self):
        assert compute_session_best([]) is None

    def test_all_none(self, make_lap):
        laps = [make_lap(1, lap_duration=None)]
        assert compute_session_best(laps) is None


class TestComputeSessionMedian:
    def test_excludes_pit_out(self, make_lap):
        laps = [
            make_lap(1, lap_duration=100.0, is_pit_out_lap=True),
            make_lap(2, lap_duration=90.0),
            make_lap(3, lap_duration=92.0),
            make_lap(4, lap_duration=94.0),
        ]
        result = compute_session_median(laps)
        assert result == 92.0  # median of [90, 92, 94]

    def test_empty(self):
        assert compute_session_median([]) is None


class TestComputeAvgLap:
    def test_excludes_pit_out(self, make_lap):
        laps = [
            make_lap(1, lap_duration=100.0, is_pit_out_lap=True),
            make_lap(2, lap_duration=90.0),
            make_lap(3, lap_duration=92.0),
        ]
        result = compute_avg_lap(laps)
        assert result == 91.0  # mean of [90, 92]

    def test_only_pit_out(self, make_lap):
        laps = [make_lap(1, lap_duration=100.0, is_pit_out_lap=True)]
        assert compute_avg_lap(laps) is None

    def test_empty(self):
        assert compute_avg_lap([]) is None


class TestNormalizeTeamColor:
    def test_with_color(self):
        assert normalize_team_color("3671C6") == "#3671C6"

    def test_none(self):
        assert normalize_team_color(None) == "#E10600"  # F1_RED

    def test_empty_string(self):
        assert normalize_team_color("") == "#E10600"


class TestAssignDriverColors:
    def test_unique_colors(self, sample_drivers):
        colors = assign_driver_colors(sample_drivers)
        assert len(colors) == 3
        assert len(set(colors.values())) == 3  # all unique

    def test_teammate_collision(self, sample_drivers):
        # VER and PER have same team_colour
        colors = assign_driver_colors(sample_drivers)
        assert colors[1] != colors[11]

    def test_single_driver(self):
        drivers = [{"driver_number": 1, "team_colour": "FF0000"}]
        colors = assign_driver_colors(drivers)
        assert colors[1] == "#FF0000"

    def test_no_team_colour(self):
        drivers = [{"driver_number": 1, "team_colour": None}]
        colors = assign_driver_colors(drivers)
        assert colors[1] == "#E10600"


class TestComputeSpeedStats:
    def test_computes_avg_and_max(self, make_lap):
        laps = [
            make_lap(1, i1=300.0, i2=280.0, st=310.0),
            make_lap(2, i1=305.0, i2=285.0, st=315.0),
        ]
        fields = [("i1_speed", "I1"), ("i2_speed", "I2"), ("st_speed", "ST")]
        result = compute_speed_stats(laps, fields)
        assert result["avgs"][0] == pytest.approx(302.5)
        assert result["maxes"][0] == 305.0
        assert result["avgs"][2] == pytest.approx(312.5)
        assert result["maxes"][2] == 315.0

    def test_missing_data(self, make_lap):
        laps = [make_lap(1, i1=None, i2=None, st=None)]
        fields = [("i1_speed", "I1")]
        result = compute_speed_stats(laps, fields)
        assert result["avgs"][0] == 0
        assert result["maxes"][0] == 0


class TestComputeIdealLap:
    def test_sums_best_sectors(self, make_lap):
        laps = [
            make_lap(1, s1=28.0, s2=35.0, s3=30.0),
            make_lap(2, s1=27.0, s2=34.0, s3=31.0),
            make_lap(3, s1=27.5, s2=34.5, s3=29.5),
        ]
        # best S1=27.0, best S2=34.0, best S3=29.5
        result = compute_ideal_lap(laps)
        assert result == pytest.approx(90.5)

    def test_missing_sector(self, make_lap):
        laps = [make_lap(1, s1=28.0, s2=None, s3=30.0)]
        assert compute_ideal_lap(laps) is None

    def test_empty(self):
        assert compute_ideal_lap([]) is None
