"""Data layer — source-agnostic repository factory and re-exports."""

from __future__ import annotations

from .source import DataSource, get_active_source
from .base import F1DataRepository
from .errors import F1DataError
from .types import CarTelemetry, DriverInfo, LapData, LocationPoint, MeetingData, PitData, SessionData, StintData, WeatherData


def get_repository() -> F1DataRepository:
    """Return the active data repository based on the user's source selection."""
    if get_active_source() == DataSource.FASTF1:
        from .fastf1_repo import FastF1Repository

        return FastF1Repository()
    from .openf1_repo import OpenF1Repository

    return OpenF1Repository()


__all__ = [
    "CarTelemetry",
    "DriverInfo",
    "F1DataError",
    "F1DataRepository",
    "LapData",
    "LocationPoint",
    "MeetingData",
    "PitData",
    "SessionData",
    "StintData",
    "WeatherData",
    "get_repository",
]
