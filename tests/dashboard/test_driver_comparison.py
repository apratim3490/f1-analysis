"""Tests for shared/services/driver_comparison.py."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from shared.data.base import F1DataRepository
from shared.data.errors import F1DataError
from shared.services.driver_comparison import (
    DriverBestLap,
    DriverComparisonService,
    DriverTelemetryTrace,
    SectorComparisonEntry,
    StintInsights,
    TelemetryPoint,
    TrackMapData,
    _estimate_stint_temperature,
)


@pytest.fixture
def make_driver_data(make_lap, make_stint):
    """Factory for per-driver data dicts."""

    def _make(driver_number: int, best_duration: float = 91.0):
        laps = [
            make_lap(i, lap_duration=best_duration + (i * 0.2), driver_number=driver_number)
            for i in range(1, 9)
        ]
        # Override first lap to be the best
        laps[0] = make_lap(1, lap_duration=best_duration, driver_number=driver_number)
        stints = [make_stint(1, "SOFT", 1, 8)]
        return {"laps": laps, "stints": stints}

    return _make


@pytest.fixture
def mock_repo(make_lap, make_stint):
    """Mock repository."""
    repo = MagicMock(spec=F1DataRepository)
    return repo


@pytest.fixture
def service(mock_repo):
    return DriverComparisonService(mock_repo)


@pytest.fixture
def two_driver_data(make_driver_data):
    return {
        1: make_driver_data(1, best_duration=90.5),
        44: make_driver_data(44, best_duration=91.0),
    }


@pytest.fixture
def two_drivers(sample_drivers):
    return [sample_drivers[0], sample_drivers[2]]  # VER and HAM


class TestFetchComparisonData:
    def test_calls_repo(self, service, mock_repo, make_lap, make_stint):
        mock_repo.get_all_laps.return_value = [make_lap(1)]
        mock_repo.get_laps.return_value = [make_lap(1)]
        mock_repo.get_stints.return_value = [make_stint(1, "SOFT", 1, 5)]
        mock_repo.get_weather.return_value = []

        driver_data, all_laps, weather = service.fetch_comparison_data(9161, [1, 44])

        mock_repo.get_all_laps.assert_called_once_with(9161)
        assert mock_repo.get_laps.call_count == 2
        assert mock_repo.get_stints.call_count == 2
        assert 1 in driver_data
        assert 44 in driver_data
        assert weather == []

    def test_weather_error_returns_empty(self, service, mock_repo, make_lap, make_stint):
        mock_repo.get_all_laps.return_value = [make_lap(1)]
        mock_repo.get_laps.return_value = [make_lap(1)]
        mock_repo.get_stints.return_value = [make_stint(1, "SOFT", 1, 5)]
        mock_repo.get_weather.side_effect = F1DataError("no weather")

        driver_data, all_laps, weather = service.fetch_comparison_data(9161, [1])

        assert weather == []
        assert 1 in driver_data


class TestComputeBestLaps:
    def test_returns_best_for_each(self, service, two_driver_data, two_drivers):
        all_laps = two_driver_data[1]["laps"] + two_driver_data[44]["laps"]
        result = service.compute_best_laps(two_driver_data, all_laps, two_drivers)

        assert len(result) == 2
        assert all(isinstance(bl, DriverBestLap) for bl in result)
        assert result[0].acronym == "VER"
        assert result[0].best_lap == 90.5
        assert result[1].acronym == "HAM"
        assert result[1].best_lap == 91.0

    def test_delta_to_session_best(self, service, two_driver_data, two_drivers):
        all_laps = two_driver_data[1]["laps"] + two_driver_data[44]["laps"]
        result = service.compute_best_laps(two_driver_data, all_laps, two_drivers)

        # VER has session best
        assert result[0].delta is not None
        assert "session best" in result[0].delta
        # HAM is slower
        assert result[1].delta is not None
        assert "+" in result[1].delta

    def test_ideal_lap(self, service, two_driver_data, two_drivers):
        all_laps = two_driver_data[1]["laps"] + two_driver_data[44]["laps"]
        result = service.compute_best_laps(two_driver_data, all_laps, two_drivers)

        for bl in result:
            assert bl.ideal_lap is not None


class TestComputeStintComparison:
    def test_returns_rows_and_insights(self, service, two_driver_data, two_drivers):
        colors = {1: "#3671C6", 44: "#E80020"}
        table_rows, raw, insights = service.compute_stint_comparison(
            two_driver_data, two_drivers, colors, is_practice=False,
        )

        assert isinstance(table_rows, list)
        assert isinstance(raw, list)
        # Both drivers have 8-lap stints, should produce rows
        assert len(table_rows) == 2
        assert table_rows[0]["Driver"] in ("VER", "HAM")

    def test_insights_structure(self, service, two_driver_data, two_drivers):
        colors = {1: "#3671C6", 44: "#E80020"}
        _, _, insights = service.compute_stint_comparison(
            two_driver_data, two_drivers, colors, is_practice=False,
        )

        assert isinstance(insights, StintInsights)
        assert len(insights.fastest_avg) == 3
        assert len(insights.most_consistent) == 3
        assert isinstance(insights.best_sectors, dict)

    def test_practice_limits_to_top3(self, service, make_lap, make_stint):
        # Create 5 stints with enough laps each
        laps = [make_lap(i, lap_duration=90.0 + (i * 0.05)) for i in range(1, 41)]
        stints = [make_stint(n, "SOFT", (n - 1) * 8 + 1, n * 8) for n in range(1, 6)]
        driver_data = {1: {"laps": laps, "stints": stints}}
        drivers = [{"driver_number": 1, "name_acronym": "VER"}]
        colors = {1: "#3671C6"}

        table_rows, _, _ = service.compute_stint_comparison(
            driver_data, drivers, colors, is_practice=True,
        )

        # Practice mode: top 3 only (but need std_dev < 2.0)
        assert len(table_rows) <= 3

    def test_empty_when_no_stints(self, service):
        driver_data = {1: {"laps": [], "stints": []}}
        drivers = [{"driver_number": 1, "name_acronym": "VER"}]
        colors = {1: "#3671C6"}

        table_rows, raw, insights = service.compute_stint_comparison(
            driver_data, drivers, colors, is_practice=False,
        )

        assert table_rows == []
        assert insights is None


class TestComputeSpeedTraps:
    def test_returns_entries(self, service, two_driver_data, two_drivers, sample_drivers):
        all_laps = two_driver_data[1]["laps"] + two_driver_data[44]["laps"]
        colors = {1: "#3671C6", 44: "#E80020"}

        entries, max_speeds, holders = service.compute_speed_traps(
            two_driver_data, all_laps, sample_drivers, two_drivers, colors,
        )

        assert len(entries) == 2
        assert entries[0]["acronym"] == "VER"
        assert len(entries[0]["max_speeds"]) == 3
        assert "I1" in max_speeds or "I2" in max_speeds or "ST" in max_speeds

    def test_session_bests(self, service, two_driver_data, two_drivers, sample_drivers):
        all_laps = two_driver_data[1]["laps"] + two_driver_data[44]["laps"]
        colors = {1: "#3671C6", 44: "#E80020"}

        _, max_speeds, holders = service.compute_speed_traps(
            two_driver_data, all_laps, sample_drivers, two_drivers, colors,
        )

        for label in max_speeds:
            assert max_speeds[label] > 0
            assert label in holders


class TestComputeSectorComparison:
    def test_returns_entries(self, service, two_driver_data, two_drivers):
        colors = {1: "#3671C6", 44: "#E80020"}
        result = service.compute_sector_comparison(two_driver_data, two_drivers, colors)

        assert len(result) == 2
        assert all(isinstance(se, SectorComparisonEntry) for se in result)
        for se in result:
            assert se.total == pytest.approx(se.s1 + se.s2 + se.s3)

    def test_frozen(self, service, two_driver_data, two_drivers):
        colors = {1: "#3671C6", 44: "#E80020"}
        result = service.compute_sector_comparison(two_driver_data, two_drivers, colors)
        with pytest.raises(AttributeError):
            result[0].s1 = 999

    def test_empty_when_no_sector_data(self, service, make_lap):
        driver_data = {
            1: {"laps": [make_lap(1, s1=None, s2=None, s3=None)]},
        }
        drivers = [{"driver_number": 1, "name_acronym": "VER"}]
        colors = {1: "#3671C6"}

        result = service.compute_sector_comparison(driver_data, drivers, colors)
        assert result == []


class TestEstimateStintTemperature:
    """Tests for the _estimate_stint_temperature helper."""

    def test_normal_case(self):
        weather = [
            {"track_temperature": 30.0, "timestamp": "2025-02-26T10:00:00"},
            {"track_temperature": 32.0, "timestamp": "2025-02-26T10:30:00"},
            {"track_temperature": 34.0, "timestamp": "2025-02-26T11:00:00"},
            {"track_temperature": 36.0, "timestamp": "2025-02-26T11:30:00"},
        ]
        # Stint covers laps 1-10 of 20 total (first half of session)
        result = _estimate_stint_temperature(weather, 1, 10, 20)
        assert result is not None
        # First half should average ~30-32
        assert 29.0 <= result <= 33.0

    def test_single_sample(self):
        weather = [{"track_temperature": 28.5, "timestamp": "2025-02-26T10:00:00"}]
        result = _estimate_stint_temperature(weather, 1, 10, 20)
        assert result == 28.5

    def test_empty_weather(self):
        result = _estimate_stint_temperature([], 1, 10, 20)
        assert result is None

    def test_none_weather(self):
        result = _estimate_stint_temperature([], 1, 10, 0)
        assert result is None

    def test_nearest_fallback(self):
        """When no samples fall in the stint window, use nearest sample."""
        weather = [
            {"track_temperature": 25.0, "timestamp": "2025-02-26T10:00:00"},
            {"track_temperature": 40.0, "timestamp": "2025-02-26T12:00:00"},
        ]
        # Stint is at very end — lap 19-20 of 20
        result = _estimate_stint_temperature(weather, 19, 20, 20)
        assert result is not None
        # Should be closer to 40 (end of session)
        assert result == 40.0

    def test_late_stint(self):
        weather = [
            {"track_temperature": 30.0, "timestamp": "2025-02-26T10:00:00"},
            {"track_temperature": 32.0, "timestamp": "2025-02-26T10:30:00"},
            {"track_temperature": 34.0, "timestamp": "2025-02-26T11:00:00"},
            {"track_temperature": 36.0, "timestamp": "2025-02-26T11:30:00"},
        ]
        # Stint covers laps 11-20 of 20 total (second half)
        result = _estimate_stint_temperature(weather, 11, 20, 20)
        assert result is not None
        # Second half should average ~34-36
        assert 33.0 <= result <= 37.0


class TestStintComparisonWithWeather:
    """Tests that weather data integrates into stint comparison."""

    def test_track_temp_column_present(self, service, two_driver_data, two_drivers):
        colors = {1: "#3671C6", 44: "#E80020"}
        weather = [
            {"track_temperature": 30.0, "timestamp": "2025-02-26T10:00:00"},
            {"track_temperature": 35.0, "timestamp": "2025-02-26T11:00:00"},
        ]
        table_rows, _, _ = service.compute_stint_comparison(
            two_driver_data, two_drivers, colors, is_practice=False,
            weather=weather,
        )
        assert len(table_rows) > 0
        assert "Track Temp" in table_rows[0]
        assert "°C" in table_rows[0]["Track Temp"]

    def test_no_track_temp_without_weather(self, service, two_driver_data, two_drivers):
        colors = {1: "#3671C6", 44: "#E80020"}
        table_rows, _, _ = service.compute_stint_comparison(
            two_driver_data, two_drivers, colors, is_practice=False,
        )
        assert len(table_rows) > 0
        assert "Track Temp" not in table_rows[0]

    def test_no_track_temp_with_empty_weather(self, service, two_driver_data, two_drivers):
        colors = {1: "#3671C6", 44: "#E80020"}
        table_rows, _, _ = service.compute_stint_comparison(
            two_driver_data, two_drivers, colors, is_practice=False,
            weather=[],
        )
        assert len(table_rows) > 0
        assert "Track Temp" not in table_rows[0]


# ── Telemetry Tests ─────────────────────────────────────────────────────────


@pytest.fixture
def telemetry_driver_data(make_lap, make_stint):
    """Driver data with date_start set for telemetry lookup."""

    def _make(driver_number: int, best_duration: float = 91.0):
        laps = [
            make_lap(
                i,
                lap_duration=best_duration + (i * 0.2),
                driver_number=driver_number,
                date_start=f"2025-03-02T14:{30 + i}:00+00:00",
            )
            for i in range(1, 9)
        ]
        laps[0] = make_lap(
            1,
            lap_duration=best_duration,
            driver_number=driver_number,
            date_start="2025-03-02T14:30:00+00:00",
        )
        stints = [make_stint(1, "SOFT", 1, 8)]
        return {"laps": laps, "stints": stints}

    return _make


class TestFetchTelemetryForBestLaps:
    def test_calls_repo_per_driver(self, service, mock_repo, telemetry_driver_data):
        dd = {
            1: telemetry_driver_data(1, 90.5),
            44: telemetry_driver_data(44, 91.0),
        }
        mock_repo.get_car_telemetry.return_value = [
            {"t": 0.0, "speed": 280, "rpm": 11000, "throttle": 100, "brake": 0, "n_gear": 7, "drs": 0},
        ]
        mock_repo.get_location.return_value = [
            {"t": 0.0, "x": 100.0, "y": 200.0, "z": 5.0},
        ]

        drivers = [
            {"driver_number": 1, "name_acronym": "VER"},
            {"driver_number": 44, "name_acronym": "HAM"},
        ]
        colors = {1: "#3671C6", 44: "#E80020"}

        result = service.fetch_telemetry_for_best_laps(9161, dd, drivers, colors)

        assert 1 in result
        assert 44 in result
        assert mock_repo.get_car_telemetry.call_count == 2
        assert mock_repo.get_location.call_count == 2

    def test_skips_driver_without_date_start(self, service, mock_repo, make_lap, make_stint):
        dd = {
            1: {
                "laps": [make_lap(1, lap_duration=90.0, date_start=None)],
                "stints": [make_stint(1, "SOFT", 1, 1)],
            },
        }
        drivers = [{"driver_number": 1, "name_acronym": "VER"}]
        colors = {1: "#3671C6"}

        result = service.fetch_telemetry_for_best_laps(9161, dd, drivers, colors)

        assert result == {}
        mock_repo.get_car_telemetry.assert_not_called()

    def test_graceful_f1_data_error(self, service, mock_repo, telemetry_driver_data):
        dd = {1: telemetry_driver_data(1, 90.5)}
        mock_repo.get_car_telemetry.side_effect = F1DataError("not supported")
        mock_repo.get_location.side_effect = F1DataError("not supported")

        drivers = [{"driver_number": 1, "name_acronym": "VER"}]
        colors = {1: "#3671C6"}

        result = service.fetch_telemetry_for_best_laps(9161, dd, drivers, colors)

        # Driver is still present, just with empty data
        assert 1 in result
        assert result[1]["car"] == []
        assert result[1]["location"] == []


class TestComputeSpeedTrace:
    def test_returns_traces(self):
        telemetry = {
            1: {
                "car": [
                    {"t": 0.0, "speed": 100, "rpm": 10000, "throttle": 100, "brake": 0, "n_gear": 3, "drs": 0},
                    {"t": 1.0, "speed": 200, "rpm": 11000, "throttle": 100, "brake": 0, "n_gear": 5, "drs": 0},
                ],
                "location": [],
                "acronym": "VER",
                "color": "#3671C6",
            },
        }
        traces = DriverComparisonService.compute_speed_trace(telemetry)

        assert len(traces) == 1
        assert isinstance(traces[0], DriverTelemetryTrace)
        assert traces[0].acronym == "VER"
        assert len(traces[0].points) == 2
        assert traces[0].points[0].value == 100.0
        assert traces[0].points[1].value == 200.0

    def test_skip_empty_car_data(self):
        telemetry = {
            1: {"car": [], "location": [], "acronym": "VER", "color": "#3671C6"},
        }
        traces = DriverComparisonService.compute_speed_trace(telemetry)
        assert traces == []


class TestComputeRpmTrace:
    def test_returns_traces(self):
        telemetry = {
            1: {
                "car": [
                    {"t": 0.0, "speed": 100, "rpm": 10000, "throttle": 100, "brake": 0, "n_gear": 3, "drs": 0},
                ],
                "location": [],
                "acronym": "VER",
                "color": "#3671C6",
            },
        }
        traces = DriverComparisonService.compute_rpm_trace(telemetry)

        assert len(traces) == 1
        assert traces[0].points[0].value == 10000.0


class TestComputeTrackMap:
    def test_none_with_no_location_data(self):
        telemetry = {
            1: {"car": [], "location": [], "acronym": "VER", "color": "#3671C6"},
        }
        result = DriverComparisonService.compute_track_map(telemetry)
        assert result is None

    def test_valid_return_with_location_data(self):
        location = [
            {"t": float(i), "x": float(i * 10), "y": float(i * 20), "z": 0.0}
            for i in range(50)
        ]
        telemetry = {
            1: {"car": [], "location": location, "acronym": "VER", "color": "#3671C6"},
            44: {"car": [], "location": location, "acronym": "HAM", "color": "#E80020"},
        }
        result = DriverComparisonService.compute_track_map(telemetry)

        assert result is not None
        assert isinstance(result, TrackMapData)
        assert len(result.track_x) == 50
        assert len(result.track_y) == 50
        assert len(result.frames) > 0
        assert "VER" in result.driver_colors
        assert "HAM" in result.driver_colors
        assert result.lap_duration > 0
