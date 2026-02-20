"""Shared fixtures for dashboard tests."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ── Mock streamlit before any dashboard imports ──────────────────────────────

_mock_st = MagicMock()
_mock_st.cache_data = lambda **kw: (lambda fn: fn)  # passthrough decorator
_mock_st.cache_resource = lambda **kw: (lambda fn: fn)  # passthrough decorator
_mock_st.session_state = {"data_source": "OpenF1"}
sys.modules.setdefault("streamlit", _mock_st)

# Add dashboard to path so `shared` is importable
_dashboard_dir = str(Path(__file__).resolve().parent.parent.parent / "dashboard")
if _dashboard_dir not in sys.path:
    sys.path.insert(0, _dashboard_dir)


# ── Sample data fixtures ─────────────────────────────────────────────────────


def _make_lap(
    lap_number: int,
    lap_duration: float | None = 93.0,
    is_pit_out_lap: bool = False,
    s1: float | None = 28.0,
    s2: float | None = 35.0,
    s3: float | None = 30.0,
    i1: float | None = 300.0,
    i2: float | None = 280.0,
    st: float | None = 310.0,
    driver_number: int = 1,
    date_start: str | None = None,
) -> dict:
    return {
        "lap_number": lap_number,
        "lap_duration": lap_duration,
        "is_pit_out_lap": is_pit_out_lap,
        "duration_sector_1": s1,
        "duration_sector_2": s2,
        "duration_sector_3": s3,
        "i1_speed": i1,
        "i2_speed": i2,
        "st_speed": st,
        "driver_number": driver_number,
        "date_start": date_start,
    }


def _make_stint(
    stint_number: int,
    compound: str,
    lap_start: int,
    lap_end: int,
    tyre_age: int = 0,
) -> dict:
    return {
        "stint_number": stint_number,
        "compound": compound,
        "lap_start": lap_start,
        "lap_end": lap_end,
        "tyre_age_at_start": tyre_age,
    }


@pytest.fixture
def sample_laps() -> list[dict]:
    """10 laps: 1 pit-out, 1 with None duration, 8 clean."""
    return [
        _make_lap(1, lap_duration=95.0, is_pit_out_lap=True),
        _make_lap(2, lap_duration=92.5, s1=27.5, s2=35.0, s3=30.0),
        _make_lap(3, lap_duration=92.0, s1=27.0, s2=35.0, s3=30.0),
        _make_lap(4, lap_duration=91.5, s1=27.0, s2=34.5, s3=30.0),
        _make_lap(5, lap_duration=93.8, s1=28.5, s2=35.2, s3=30.1),
        _make_lap(6, lap_duration=None),
        _make_lap(7, lap_duration=92.0, s1=27.0, s2=35.0, s3=30.0),
        _make_lap(8, lap_duration=91.0, s1=26.5, s2=34.5, s3=30.0),
        _make_lap(9, lap_duration=92.5, s1=27.5, s2=35.0, s3=30.0),
        _make_lap(10, lap_duration=93.0, s1=28.0, s2=35.0, s3=30.0),
    ]


@pytest.fixture
def sample_all_laps(sample_laps: list[dict]) -> list[dict]:
    """Session laps from multiple drivers."""
    driver2_laps = [
        _make_lap(1, lap_duration=94.0, driver_number=2),
        _make_lap(2, lap_duration=91.0, driver_number=2, s1=26.5, s2=34.5, s3=30.0),
        _make_lap(3, lap_duration=90.5, driver_number=2, s1=26.0, s2=34.5, s3=30.0),
        _make_lap(4, lap_duration=91.5, driver_number=2, s1=27.0, s2=34.5, s3=30.0),
        _make_lap(5, lap_duration=92.0, driver_number=2, s1=27.0, s2=35.0, s3=30.0),
    ]
    return sample_laps + driver2_laps


@pytest.fixture
def sample_stints() -> list[dict]:
    return [
        _make_stint(1, "SOFT", 1, 5),
        _make_stint(2, "MEDIUM", 6, 10, tyre_age=0),
    ]


@pytest.fixture
def sample_pits() -> list[dict]:
    return [
        {"lap_number": 5, "pit_duration": 23.5},
        {"lap_number": 15, "pit_duration": 24.1},
    ]


@pytest.fixture
def sample_drivers() -> list[dict]:
    return [
        {
            "driver_number": 1,
            "name_acronym": "VER",
            "full_name": "Max Verstappen",
            "team_name": "Red Bull Racing",
            "team_colour": "3671C6",
            "headshot_url": "https://example.com/ver.png",
        },
        {
            "driver_number": 11,
            "name_acronym": "PER",
            "full_name": "Sergio Perez",
            "team_name": "Red Bull Racing",
            "team_colour": "3671C6",
            "headshot_url": "https://example.com/per.png",
        },
        {
            "driver_number": 44,
            "name_acronym": "HAM",
            "full_name": "Lewis Hamilton",
            "team_name": "Ferrari",
            "team_colour": "E80020",
            "headshot_url": None,
        },
    ]


@pytest.fixture
def make_lap():
    """Factory fixture for creating lap dicts."""
    return _make_lap


@pytest.fixture
def make_stint():
    """Factory fixture for creating stint dicts."""
    return _make_stint
