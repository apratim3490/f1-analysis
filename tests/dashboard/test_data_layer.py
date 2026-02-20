"""Tests for shared/data/ — errors, types, base, and factory."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from shared.data.base import F1DataRepository
from shared.data.errors import F1DataError
from shared.data.types import (
    CarTelemetry,
    DriverInfo,
    LapData,
    LocationPoint,
    MeetingData,
    PitData,
    SessionData,
    StintData,
)


class TestF1DataError:
    def test_is_exception(self):
        assert issubclass(F1DataError, Exception)

    def test_message(self):
        err = F1DataError("test message")
        assert str(err) == "test message"

    def test_catchable(self):
        with pytest.raises(F1DataError):
            raise F1DataError("boom")


class TestF1DataRepository:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            F1DataRepository()

    def test_concrete_implementation(self):
        """A class implementing all methods can be instantiated."""

        class ConcreteRepo(F1DataRepository):
            def get_meetings(self, year): return []
            def get_sessions(self, meeting_key): return []
            def get_drivers(self, session_key): return []
            def get_laps(self, session_key, driver_number): return []
            def get_all_laps(self, session_key): return []
            def get_stints(self, session_key, driver_number): return []
            def get_pits(self, session_key, driver_number): return []
            def get_weather(self, session_key): return []
            def get_car_telemetry(self, session_key, driver_number, date_start, date_end): return []
            def get_location(self, session_key, driver_number, date_start, date_end): return []

        repo = ConcreteRepo()
        assert repo.get_meetings(2024) == []

    def test_partial_implementation_fails(self):
        """A class missing methods cannot be instantiated."""

        class PartialRepo(F1DataRepository):
            def get_meetings(self, year): return []

        with pytest.raises(TypeError):
            PartialRepo()


class TestTypedDicts:
    def test_driver_info(self):
        d: DriverInfo = {
            "driver_number": 1,
            "name_acronym": "VER",
            "full_name": "Max Verstappen",
            "team_name": "Red Bull Racing",
            "team_colour": "3671C6",
            "headshot_url": None,
        }
        assert d["driver_number"] == 1

    def test_lap_data(self):
        lap: LapData = {
            "lap_number": 5,
            "lap_duration": 93.8,
            "is_pit_out_lap": False,
            "duration_sector_1": 28.5,
            "duration_sector_2": 35.2,
            "duration_sector_3": 30.1,
            "i1_speed": 305.0,
            "i2_speed": 280.0,
            "st_speed": 310.0,
            "driver_number": 1,
            "date_start": "2025-03-02T14:30:00+00:00",
        }
        assert lap["lap_duration"] == 93.8
        assert lap["date_start"] is not None

    def test_car_telemetry(self):
        ct: CarTelemetry = {
            "t": 5.2,
            "speed": 280,
            "rpm": 11500,
            "throttle": 100,
            "brake": 0,
            "n_gear": 7,
            "drs": 12,
        }
        assert ct["speed"] == 280

    def test_location_point(self):
        lp: LocationPoint = {
            "t": 5.2,
            "x": 1234.5,
            "y": 6789.0,
            "z": 10.5,
        }
        assert lp["x"] == 1234.5

    def test_stint_data(self):
        stint: StintData = {
            "stint_number": 1,
            "compound": "SOFT",
            "lap_start": 1,
            "lap_end": 20,
            "tyre_age_at_start": 0,
        }
        assert stint["compound"] == "SOFT"

    def test_pit_data(self):
        pit: PitData = {
            "lap_number": 15,
            "pit_duration": 23.5,
        }
        assert pit["pit_duration"] == 23.5

    def test_meeting_data(self):
        m: MeetingData = {
            "meeting_name": "Bahrain Grand Prix",
            "meeting_key": 1219,
        }
        assert m["meeting_name"] == "Bahrain Grand Prix"

    def test_session_data(self):
        s: SessionData = {
            "session_name": "Race",
            "session_key": 9161,
            "session_type": "Race",
        }
        assert s["session_type"] == "Race"


class TestKeyParsing:
    """Tests for FastF1 composite key parsing."""

    def test_parse_session_key_standard(self):
        from shared.data.fastf1_repo import _parse_session_key

        year, event, sess, occ = _parse_session_key("2026|Bahrain Grand Prix|Race")
        assert year == 2026
        assert event == "Bahrain Grand Prix"
        assert sess == "Race"
        assert occ is None

    def test_parse_session_key_with_occurrence(self):
        from shared.data.fastf1_repo import _parse_session_key

        year, event, sess, occ = _parse_session_key("2026|Pre-Season Testing|2|Practice 1")
        assert year == 2026
        assert event == "Pre-Season Testing"
        assert sess == "Practice 1"
        assert occ == 2

    def test_parse_session_key_invalid(self):
        from shared.data.fastf1_repo import _parse_session_key

        with pytest.raises(F1DataError):
            _parse_session_key("2026|only_two")
        with pytest.raises(F1DataError):
            _parse_session_key("bad")

    def test_parse_meeting_key_standard(self):
        from shared.data.fastf1_repo import _parse_meeting_key

        year, name, occ = _parse_meeting_key("2026|Bahrain Grand Prix")
        assert year == 2026
        assert name == "Bahrain Grand Prix"
        assert occ is None

    def test_parse_meeting_key_with_occurrence(self):
        from shared.data.fastf1_repo import _parse_meeting_key

        year, name, occ = _parse_meeting_key("2026|Pre-Season Testing|2")
        assert year == 2026
        assert name == "Pre-Season Testing"
        assert occ == 2

    def test_parse_meeting_key_invalid(self):
        from shared.data.fastf1_repo import _parse_meeting_key

        with pytest.raises(F1DataError):
            _parse_meeting_key("bad")
        with pytest.raises(F1DataError):
            _parse_meeting_key("2026|a|b|c")


class TestGetRepository:
    def test_returns_openf1_by_default(self):
        from shared.data import get_repository
        from shared.data.openf1_repo import OpenF1Repository

        repo = get_repository()
        assert isinstance(repo, OpenF1Repository)

    def test_returns_fastf1_when_selected(self):
        import streamlit as st

        st.session_state["data_source"] = "FastF1"
        try:
            from shared.data import get_repository
            from shared.data.fastf1_repo import FastF1Repository

            repo = get_repository()
            assert isinstance(repo, FastF1Repository)
        finally:
            st.session_state["data_source"] = "OpenF1"
