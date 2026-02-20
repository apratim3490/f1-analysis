"""Tests for shared/services/driver_performance.py."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from shared.data.base import F1DataRepository
from shared.services.driver_performance import (
    DriverKPIs,
    DriverPerformanceService,
    LapProgressionData,
    SectorBreakdownData,
    SpeedTrapData,
    TireStrategyData,
)


@pytest.fixture
def mock_repo(sample_laps, sample_all_laps, sample_stints, sample_pits):
    """Mock repository returning sample data."""
    repo = MagicMock(spec=F1DataRepository)
    repo.get_laps.return_value = sample_laps
    repo.get_all_laps.return_value = sample_all_laps
    repo.get_stints.return_value = sample_stints
    repo.get_pits.return_value = sample_pits
    return repo


@pytest.fixture
def service(mock_repo):
    return DriverPerformanceService(mock_repo)


class TestFetchDriverData:
    def test_calls_all_repo_methods(self, service, mock_repo):
        laps, all_laps, stints, pits = service.fetch_driver_data(9161, 1)
        mock_repo.get_laps.assert_called_once_with(9161, 1)
        mock_repo.get_all_laps.assert_called_once_with(9161)
        mock_repo.get_stints.assert_called_once_with(9161, 1)
        mock_repo.get_pits.assert_called_once_with(9161, 1)
        assert len(laps) == 10
        assert len(pits) == 2


class TestComputeKPIs:
    def test_practice_kpis(self, service, sample_laps, sample_all_laps, sample_pits):
        kpis = service.compute_kpis(sample_laps, sample_all_laps, sample_pits, is_practice=True)
        assert isinstance(kpis, DriverKPIs)
        assert kpis.total_laps == 10
        assert kpis.best_lap == 91.0  # lap 8
        assert kpis.session_best == 90.5  # driver 2
        assert kpis.avg_lap is None  # not shown in practice
        assert kpis.pit_count is None  # not shown in practice

    def test_race_kpis(self, service, sample_laps, sample_all_laps, sample_pits):
        kpis = service.compute_kpis(sample_laps, sample_all_laps, sample_pits, is_practice=False)
        assert kpis.avg_lap is not None
        assert kpis.pit_count == 2
        assert kpis.best_lap_delta is not None

    def test_kpis_frozen(self, service, sample_laps, sample_all_laps, sample_pits):
        kpis = service.compute_kpis(sample_laps, sample_all_laps, sample_pits, is_practice=False)
        with pytest.raises(AttributeError):
            kpis.total_laps = 999


class TestPrepareLapProgression:
    def test_race_mode(self, service, sample_laps, sample_all_laps, sample_stints):
        result = service.prepare_lap_progression(
            sample_laps, sample_all_laps, sample_stints, is_practice=False,
        )
        assert isinstance(result, LapProgressionData)
        assert len(result.clean_laps) == 8
        assert len(result.pit_out_laps) == 1
        assert result.session_median is not None
        assert result.session_best is not None
        assert result.compound_groups is None  # not practice

    def test_practice_mode(self, service, sample_laps, sample_all_laps, sample_stints):
        result = service.prepare_lap_progression(
            sample_laps, sample_all_laps, sample_stints, is_practice=True,
        )
        assert result.compound_groups is not None
        assert isinstance(result.edge_excluded_laps, frozenset)


class TestPrepareSectorBreakdown:
    def test_filters_incomplete_sectors(self, service, sample_laps, sample_stints):
        result = service.prepare_sector_breakdown(sample_laps, sample_stints, is_practice=False)
        assert isinstance(result, SectorBreakdownData)
        # All laps with non-None sectors, excluding pit-out
        for lap in result.sector_laps:
            assert lap["duration_sector_1"] is not None
            assert lap["duration_sector_2"] is not None
            assert lap["duration_sector_3"] is not None
            assert not lap.get("is_pit_out_lap")
        assert result.compounds is None  # not practice

    def test_practice_includes_compounds(self, service, sample_laps, sample_stints):
        result = service.prepare_sector_breakdown(sample_laps, sample_stints, is_practice=True)
        assert result.compounds is not None
        assert len(result.compounds) == len(result.sector_laps)


class TestPrepareSpeedTraps:
    def test_has_data(self, service, sample_laps, sample_all_laps):
        result = service.prepare_speed_traps(sample_laps, sample_all_laps)
        assert isinstance(result, SpeedTrapData)
        assert result.has_data is True
        assert len(result.categories) == 3
        assert len(result.driver_avgs) == 3
        assert len(result.driver_maxes) == 3
        assert len(result.session_bests) == 3

    def test_no_speed_data(self, service, make_lap):
        laps = [make_lap(1, i1=None, i2=None, st=None)]
        result = service.prepare_speed_traps(laps, laps)
        assert result.has_data is False
        assert result.categories == []


class TestPrepareStintSummaries:
    def test_filters_short_stints(self, service, make_lap, make_stint):
        # Create a stint with only 3 laps
        laps = [make_lap(i, lap_duration=90.0 + i) for i in range(1, 4)]
        stints = [make_stint(1, "SOFT", 1, 3)]
        result = service.prepare_stint_summaries(laps, stints)
        assert len(result) == 0  # < 5 laps

    def test_keeps_long_stints(self, service, make_lap, make_stint):
        laps = [make_lap(i, lap_duration=90.0 + (i * 0.1)) for i in range(1, 9)]
        stints = [make_stint(1, "SOFT", 1, 8)]
        result = service.prepare_stint_summaries(laps, stints)
        assert len(result) == 1
        assert result[0]["compound"] == "SOFT"


class TestGetTireStrategy:
    def test_returns_stints(self, service, sample_stints):
        result = service.get_tire_strategy(sample_stints)
        assert isinstance(result, TireStrategyData)
        assert result.stints == sample_stints
