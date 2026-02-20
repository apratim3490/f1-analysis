"""Abstract base repository for F1 data access."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .types import CarTelemetry, DriverInfo, LapData, LocationPoint, MeetingData, PitData, SessionData, StintData, WeatherData


class F1DataRepository(ABC):
    """Source-agnostic interface for F1 data access."""

    @abstractmethod
    def get_meetings(self, year: int) -> list[MeetingData]: ...

    @abstractmethod
    def get_sessions(self, meeting_key: int | str) -> list[SessionData]: ...

    @abstractmethod
    def get_drivers(self, session_key: int | str) -> list[DriverInfo]: ...

    @abstractmethod
    def get_laps(self, session_key: int | str, driver_number: int) -> list[LapData]: ...

    @abstractmethod
    def get_all_laps(self, session_key: int | str) -> list[LapData]: ...

    @abstractmethod
    def get_stints(self, session_key: int | str, driver_number: int) -> list[StintData]: ...

    @abstractmethod
    def get_pits(self, session_key: int | str, driver_number: int) -> list[PitData]: ...

    @abstractmethod
    def get_weather(self, session_key: int | str) -> list[WeatherData]: ...

    @abstractmethod
    def get_car_telemetry(
        self, session_key: int | str, driver_number: int, date_start: str, date_end: str,
    ) -> list[CarTelemetry]: ...

    @abstractmethod
    def get_location(
        self, session_key: int | str, driver_number: int, date_start: str, date_end: str,
    ) -> list[LocationPoint]: ...
