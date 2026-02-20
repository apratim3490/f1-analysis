"""Tests for shared/services/stint_helpers.py — stint summarisation and compound lookup."""

from __future__ import annotations

import pytest

from shared.services.stint_helpers import (
    get_compound_for_lap,
    summarise_stints,
    summarise_stints_with_sectors,
)


class TestGetCompoundForLap:
    def test_finds_correct_compound(self, sample_stints):
        assert get_compound_for_lap(1, sample_stints) == "SOFT"
        assert get_compound_for_lap(5, sample_stints) == "SOFT"
        assert get_compound_for_lap(6, sample_stints) == "MEDIUM"
        assert get_compound_for_lap(10, sample_stints) == "MEDIUM"

    def test_unknown_for_gap(self, sample_stints):
        assert get_compound_for_lap(99, sample_stints) == "UNKNOWN"

    def test_empty_stints(self):
        assert get_compound_for_lap(1, []) == "UNKNOWN"


class TestSummariseStints:
    def test_basic_summary(self, make_lap, make_stint):
        laps = [make_lap(i, lap_duration=90.0 + (i * 0.1)) for i in range(1, 9)]
        stints = [make_stint(1, "SOFT", 1, 8)]

        result = summarise_stints(laps, stints)
        assert len(result) == 1
        assert result[0]["compound"] == "SOFT"
        assert result[0]["stint_number"] == 1
        assert result[0]["avg_time"] > 0
        assert result[0]["best_time"] > 0
        assert result[0]["std_dev"] >= 0

    def test_excludes_pit_out_laps(self, make_lap, make_stint):
        laps = [
            make_lap(1, lap_duration=95.0, is_pit_out_lap=True),
            make_lap(2, lap_duration=90.0),
            make_lap(3, lap_duration=90.5),
            make_lap(4, lap_duration=91.0),
        ]
        stints = [make_stint(1, "SOFT", 1, 4)]

        result = summarise_stints(laps, stints)
        assert result[0]["num_laps"] == 3  # pit-out excluded

    def test_edge_outlier_trimming(self, make_lap, make_stint):
        # First lap is a warm-up outlier (much slower)
        laps = [
            make_lap(1, lap_duration=120.0),  # outlier
            make_lap(2, lap_duration=90.0),
            make_lap(3, lap_duration=90.5),
            make_lap(4, lap_duration=91.0),
            make_lap(5, lap_duration=90.0),  # last lap, not outlier
        ]
        stints = [make_stint(1, "SOFT", 1, 5)]

        result = summarise_stints(laps, stints)
        assert 1 in result[0]["excluded_laps"]  # lap 1 excluded
        assert result[0]["num_laps"] == 4  # 5 - 1 excluded

    def test_empty_stints(self, sample_laps):
        result = summarise_stints(sample_laps, [])
        assert result == []

    def test_no_valid_laps(self, make_lap, make_stint):
        laps = [make_lap(1, lap_duration=None)]
        stints = [make_stint(1, "SOFT", 1, 1)]
        result = summarise_stints(laps, stints)
        assert result == []


class TestSummariseStintsWithSectors:
    def test_includes_sector_data(self, make_lap, make_stint):
        laps = [
            make_lap(i, lap_duration=90.0 + i * 0.1, s1=27.0 + i * 0.05, s2=34.0, s3=29.0)
            for i in range(1, 9)
        ]
        stints = [make_stint(1, "MEDIUM", 1, 8)]

        result = summarise_stints_with_sectors(laps, stints)
        assert len(result) == 1
        s = result[0]
        assert s["avg_sector_1"] is not None
        assert s["avg_sector_2"] is not None
        assert s["avg_sector_3"] is not None
        assert s["best_sector_1"] is not None
        assert s["best_sector_2"] is not None
        assert s["best_sector_3"] is not None

    def test_sector_best_is_minimum(self, make_lap, make_stint):
        laps = [
            make_lap(1, lap_duration=90.0, s1=28.0, s2=34.0, s3=28.0),
            make_lap(2, lap_duration=89.0, s1=27.0, s2=33.0, s3=29.0),
            make_lap(3, lap_duration=91.0, s1=29.0, s2=35.0, s3=27.0),
        ]
        stints = [make_stint(1, "SOFT", 1, 3)]

        result = summarise_stints_with_sectors(laps, stints)
        assert result[0]["best_sector_1"] == 27.0
        assert result[0]["best_sector_2"] == 33.0
        assert result[0]["best_sector_3"] == 27.0

    def test_handles_missing_sectors(self, make_lap, make_stint):
        laps = [
            make_lap(1, lap_duration=90.0, s1=28.0, s2=34.0, s3=28.0),
            make_lap(2, lap_duration=89.0, s1=None, s2=None, s3=None),
        ]
        stints = [make_stint(1, "SOFT", 1, 2)]

        result = summarise_stints_with_sectors(laps, stints)
        # Should still compute from the one lap with sectors
        assert result[0]["avg_sector_1"] == 28.0
        assert result[0]["num_laps"] == 2  # both count for lap time
