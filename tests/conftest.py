"""Shared test fixtures and sample API responses."""

from __future__ import annotations

import pytest

from openf1 import OpenF1Client
from openf1._http import SyncTransport

BASE_URL = "https://api.openf1.org/v1"


SAMPLE_DRIVER = {
    "broadcast_name": "M VERSTAPPEN",
    "country_code": "NED",
    "driver_number": 1,
    "first_name": "Max",
    "full_name": "Max VERSTAPPEN",
    "headshot_url": "https://example.com/ver.png",
    "last_name": "Verstappen",
    "meeting_key": 1219,
    "name_acronym": "VER",
    "session_key": 9161,
    "team_colour": "3671C6",
    "team_name": "Red Bull Racing",
}

SAMPLE_SESSION = {
    "circuit_key": 61,
    "circuit_short_name": "Bahrain",
    "country_code": "BHR",
    "country_key": 36,
    "country_name": "Bahrain",
    "date_end": "2023-03-05T17:02:48",
    "date_start": "2023-03-05T15:00:00",
    "gmt_offset": "03:00:00",
    "location": "Sakhir",
    "meeting_key": 1219,
    "session_key": 9161,
    "session_name": "Race",
    "session_type": "Race",
    "year": 2023,
}

SAMPLE_LAP = {
    "date_start": "2023-03-05T15:10:00",
    "driver_number": 1,
    "duration_sector_1": 28.5,
    "duration_sector_2": 35.2,
    "duration_sector_3": 30.1,
    "i1_speed": 305.0,
    "i2_speed": 280.0,
    "is_pit_out_lap": False,
    "lap_duration": 93.8,
    "lap_number": 5,
    "meeting_key": 1219,
    "segments_sector_1": [2048, 2049, 2051],
    "segments_sector_2": [2048, 2049],
    "segments_sector_3": [2048, 2049, 2050],
    "session_key": 9161,
    "st_speed": 310.0,
}

SAMPLE_WEATHER = {
    "air_temperature": 30.5,
    "date": "2023-03-05T15:00:00",
    "humidity": 45.0,
    "meeting_key": 1219,
    "pressure": 1013.0,
    "rainfall": 0,
    "session_key": 9161,
    "track_temperature": 45.2,
    "wind_direction": 180,
    "wind_speed": 3.5,
}

SAMPLE_PIT = {
    "date": "2023-03-05T15:30:00",
    "driver_number": 1,
    "lap_number": 15,
    "meeting_key": 1219,
    "pit_duration": 23.5,
    "session_key": 9161,
}

SAMPLE_CAR_DATA = {
    "brake": 0,
    "date": "2023-03-05T15:10:00.100",
    "driver_number": 1,
    "drs": 12,
    "meeting_key": 1219,
    "n_gear": 7,
    "rpm": 10500,
    "session_key": 9161,
    "speed": 305,
    "throttle": 100,
}

SAMPLE_STINT = {
    "compound": "SOFT",
    "driver_number": 1,
    "lap_end": 20,
    "lap_start": 1,
    "meeting_key": 1219,
    "session_key": 9161,
    "stint_number": 1,
    "tyre_age_at_start": 0,
}


@pytest.fixture
def base_url() -> str:
    return BASE_URL
