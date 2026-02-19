"""Tests for Pydantic model deserialization."""

from __future__ import annotations

from datetime import timedelta

import pytest

from openf1.models.car_data import CarData
from openf1.models.championship import ChampionshipDriver, ChampionshipTeam
from openf1.models.driver import Driver
from openf1.models.interval import Interval
from openf1.models.lap import Lap
from openf1.models.location import Location
from openf1.models.meeting import Meeting
from openf1.models.overtake import Overtake
from openf1.models.pit import Pit
from openf1.models.position import Position
from openf1.models.race_control import RaceControl
from openf1.models.session import Session
from openf1.models.session_result import SessionResult
from openf1.models.starting_grid import StartingGrid
from openf1.models.stint import Stint
from openf1.models.team_radio import TeamRadio
from openf1.models.weather import Weather
from tests.conftest import (
    SAMPLE_CAR_DATA,
    SAMPLE_DRIVER,
    SAMPLE_LAP,
    SAMPLE_PIT,
    SAMPLE_SESSION,
    SAMPLE_STINT,
    SAMPLE_WEATHER,
)


class TestDriverModel:
    def test_parse(self) -> None:
        driver = Driver.model_validate(SAMPLE_DRIVER)
        assert driver.driver_number == 1
        assert driver.full_name == "Max VERSTAPPEN"
        assert driver.team_name == "Red Bull Racing"
        assert driver.name_acronym == "VER"

    def test_frozen(self) -> None:
        driver = Driver.model_validate(SAMPLE_DRIVER)
        with pytest.raises(Exception):
            driver.driver_number = 44  # type: ignore[misc]

    def test_optional_fields(self) -> None:
        driver = Driver.model_validate({"driver_number": 1})
        assert driver.full_name is None
        assert driver.team_name is None


class TestSessionModel:
    def test_parse(self) -> None:
        session = Session.model_validate(SAMPLE_SESSION)
        assert session.session_key == 9161
        assert session.session_name == "Race"
        assert session.circuit_short_name == "Bahrain"
        assert session.year == 2023

    def test_datetime_parsing(self) -> None:
        session = Session.model_validate(SAMPLE_SESSION)
        assert session.date_start is not None
        assert session.date_start.year == 2023
        assert session.date_start.month == 3


class TestLapModel:
    def test_parse(self) -> None:
        lap = Lap.model_validate(SAMPLE_LAP)
        assert lap.driver_number == 1
        assert lap.lap_number == 5
        assert lap.lap_duration == 93.8
        assert lap.is_pit_out_lap is False

    def test_total_sector_time(self) -> None:
        lap = Lap.model_validate(SAMPLE_LAP)
        assert lap.total_sector_time is not None
        assert abs(lap.total_sector_time - 93.8) < 0.01

    def test_total_sector_time_missing(self) -> None:
        lap = Lap.model_validate({"lap_number": 1})
        assert lap.total_sector_time is None

    def test_lap_timedelta(self) -> None:
        lap = Lap.model_validate(SAMPLE_LAP)
        assert lap.lap_timedelta == timedelta(seconds=93.8)

    def test_lap_timedelta_missing(self) -> None:
        lap = Lap.model_validate({"lap_number": 1})
        assert lap.lap_timedelta is None

    def test_segments(self) -> None:
        lap = Lap.model_validate(SAMPLE_LAP)
        assert lap.segments_sector_1 == [2048, 2049, 2051]


class TestWeatherModel:
    def test_parse(self) -> None:
        weather = Weather.model_validate(SAMPLE_WEATHER)
        assert weather.air_temperature == 30.5
        assert weather.track_temperature == 45.2
        assert weather.rainfall == 0


class TestCarDataModel:
    def test_parse(self) -> None:
        data = CarData.model_validate(SAMPLE_CAR_DATA)
        assert data.speed == 305
        assert data.n_gear == 7
        assert data.rpm == 10500
        assert data.throttle == 100


class TestPitModel:
    def test_parse(self) -> None:
        pit = Pit.model_validate(SAMPLE_PIT)
        assert pit.driver_number == 1
        assert pit.lap_number == 15
        assert pit.pit_duration == 23.5


class TestStintModel:
    def test_parse(self) -> None:
        stint = Stint.model_validate(SAMPLE_STINT)
        assert stint.compound == "SOFT"
        assert stint.lap_start == 1
        assert stint.lap_end == 20
        assert stint.tyre_age_at_start == 0


class TestChampionshipModels:
    def test_driver_standing(self) -> None:
        data = {"driver_number": 1, "points": 575.0, "position": 1, "team_name": "Red Bull Racing"}
        standing = ChampionshipDriver.model_validate(data)
        assert standing.points == 575.0
        assert standing.position == 1

    def test_team_standing(self) -> None:
        data = {"team_name": "Red Bull Racing", "points": 860.0, "position": 1}
        standing = ChampionshipTeam.model_validate(data)
        assert standing.points == 860.0


class TestRemainingModels:
    def test_interval(self) -> None:
        data = {"driver_number": 1, "gap_to_leader": 0.0, "interval": 0.0}
        interval = Interval.model_validate(data)
        assert interval.gap_to_leader == 0.0

    def test_location(self) -> None:
        data = {"driver_number": 1, "x": 1234.5, "y": 6789.0, "z": 0.0}
        loc = Location.model_validate(data)
        assert loc.x == 1234.5

    def test_meeting(self) -> None:
        data = {"meeting_key": 1219, "meeting_name": "Bahrain Grand Prix", "year": 2023}
        meeting = Meeting.model_validate(data)
        assert meeting.meeting_name == "Bahrain Grand Prix"

    def test_overtake(self) -> None:
        data = {"driver_number": 1, "overtaking_driver_number": 11, "lap_number": 5}
        overtake = Overtake.model_validate(data)
        assert overtake.overtaking_driver_number == 11

    def test_position(self) -> None:
        data = {"driver_number": 1, "position": 1}
        pos = Position.model_validate(data)
        assert pos.position == 1

    def test_race_control(self) -> None:
        data = {"category": "Flag", "flag": "GREEN", "message": "GREEN LIGHT"}
        rc = RaceControl.model_validate(data)
        assert rc.flag == "GREEN"

    def test_session_result(self) -> None:
        data = {"driver_number": 1, "position": 1, "status": "Finished", "laps_completed": 57}
        result = SessionResult.model_validate(data)
        assert result.laps_completed == 57

    def test_starting_grid(self) -> None:
        data = {"driver_number": 1, "position": 1, "qualifying_time": "1:29.708"}
        grid = StartingGrid.model_validate(data)
        assert grid.qualifying_time == "1:29.708"

    def test_team_radio(self) -> None:
        data = {"driver_number": 1, "recording_url": "https://example.com/radio.mp3"}
        radio = TeamRadio.model_validate(data)
        assert radio.recording_url == "https://example.com/radio.mp3"
