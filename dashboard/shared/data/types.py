"""Data contracts for the F1 dashboard data layer."""

from __future__ import annotations

from typing import TypedDict


class DriverInfo(TypedDict):
    driver_number: int
    name_acronym: str
    full_name: str
    team_name: str
    team_colour: str | None
    headshot_url: str | None


class LapData(TypedDict):
    lap_number: int
    lap_duration: float | None
    is_pit_out_lap: bool
    duration_sector_1: float | None
    duration_sector_2: float | None
    duration_sector_3: float | None
    i1_speed: float | None
    i2_speed: float | None
    st_speed: float | None
    driver_number: int
    date_start: str | None


class StintData(TypedDict):
    stint_number: int
    compound: str
    lap_start: int
    lap_end: int
    tyre_age_at_start: int


class PitData(TypedDict):
    lap_number: int
    pit_duration: float | None


class MeetingData(TypedDict):
    meeting_name: str
    meeting_key: int | str


class SessionData(TypedDict):
    session_name: str
    session_key: int | str
    session_type: str


class CarTelemetry(TypedDict):
    t: float  # seconds into lap
    speed: int
    rpm: int
    throttle: int
    brake: int
    n_gear: int
    drs: int


class LocationPoint(TypedDict):
    t: float  # seconds into lap
    x: float
    y: float
    z: float


class WeatherData(TypedDict):
    track_temperature: float
    timestamp: str  # ISO 8601
