"""OpenF1 API repository implementation."""

from __future__ import annotations

import threading
import time

import streamlit as st

from datetime import datetime

from openf1 import Filter, OpenF1Client

from .base import F1DataRepository
from .errors import F1DataError
from ..api_logging import log_api_call
from .types import CarTelemetry, DriverInfo, LapData, LocationPoint, MeetingData, PitData, SessionData, StintData, WeatherData

# ── Rate limiting ────────────────────────────────────────────────────────────

_last_request_time: float = 0.0
_rate_limit_lock = threading.Lock()
_MIN_REQUEST_INTERVAL = 0.35  # OpenF1 allows 3 req/s; 350ms keeps us safe


def _rate_limit() -> None:
    """Sleep if needed to respect the OpenF1 API rate limit."""
    global _last_request_time
    with _rate_limit_lock:
        now = time.monotonic()
        elapsed = now - _last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL:
            time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
        _last_request_time = time.monotonic()


# ── Cached fetch helpers ─────────────────────────────────────────────────────


@st.cache_data(ttl=600)
def _fetch_meetings(year: int) -> list[MeetingData]:
    _rate_limit()
    try:
        with OpenF1Client() as f1:
            return [m.model_dump() for m in f1.meetings(year=year)]
    except Exception as exc:
        raise F1DataError(f"Failed to fetch meetings for {year}: {exc}") from exc


@st.cache_data(ttl=600)
def _fetch_sessions(meeting_key: int) -> list[SessionData]:
    _rate_limit()
    try:
        with OpenF1Client() as f1:
            return [s.model_dump() for s in f1.sessions(meeting_key=meeting_key)]
    except Exception as exc:
        raise F1DataError(f"Failed to fetch sessions for meeting {meeting_key}: {exc}") from exc


@st.cache_data(ttl=600)
def _fetch_drivers(session_key: int) -> list[DriverInfo]:
    _rate_limit()
    try:
        with OpenF1Client() as f1:
            return [d.model_dump() for d in f1.drivers(session_key=session_key)]
    except Exception as exc:
        raise F1DataError(f"Failed to fetch drivers for session {session_key}: {exc}") from exc


def _normalize_lap_dict(lap: object) -> LapData:
    """Convert a Lap model to LapData dict, adding date_start as ISO string."""
    d = lap.model_dump()  # type: ignore[union-attr]
    ds = d.pop("date_start", None)
    d["date_start"] = ds.isoformat() if isinstance(ds, datetime) else None
    # Remove fields not in LapData contract
    for key in list(d):
        if key not in LapData.__annotations__:
            del d[key]
    return d  # type: ignore[return-value]


@st.cache_data(ttl=600)
def _fetch_laps(session_key: int, driver_number: int) -> list[LapData]:
    _rate_limit()
    try:
        with OpenF1Client() as f1:
            return [
                _normalize_lap_dict(lap) for lap in f1.laps(
                    session_key=session_key, driver_number=driver_number,
                )
            ]
    except Exception as exc:
        raise F1DataError(
            f"Failed to fetch laps for driver {driver_number} in session {session_key}: {exc}",
        ) from exc


@st.cache_data(ttl=600)
def _fetch_all_laps(session_key: int) -> list[LapData]:
    _rate_limit()
    try:
        with OpenF1Client() as f1:
            return [_normalize_lap_dict(lap) for lap in f1.laps(session_key=session_key)]
    except Exception as exc:
        raise F1DataError(f"Failed to fetch all laps for session {session_key}: {exc}") from exc


@st.cache_data(ttl=600)
def _fetch_stints(session_key: int, driver_number: int) -> list[StintData]:
    _rate_limit()
    try:
        with OpenF1Client() as f1:
            return [
                s.model_dump() for s in f1.stints(
                    session_key=session_key, driver_number=driver_number,
                )
            ]
    except Exception as exc:
        raise F1DataError(
            f"Failed to fetch stints for driver {driver_number} in session {session_key}: {exc}",
        ) from exc


@st.cache_data(ttl=600)
def _fetch_weather(session_key: int) -> list[WeatherData]:
    _rate_limit()
    try:
        with OpenF1Client() as f1:
            return [
                {
                    "track_temperature": w.track_temperature,
                    "timestamp": w.date.isoformat(),
                }
                for w in f1.weather(session_key=session_key)
                if w.track_temperature is not None and w.date is not None
            ]
    except Exception as exc:
        raise F1DataError(f"Failed to fetch weather for session {session_key}: {exc}") from exc


@st.cache_data(ttl=600)
def _fetch_pits(session_key: int, driver_number: int) -> list[PitData]:
    _rate_limit()
    try:
        with OpenF1Client() as f1:
            return [
                p.model_dump() for p in f1.pit(
                    session_key=session_key, driver_number=driver_number,
                )
            ]
    except Exception as exc:
        raise F1DataError(
            f"Failed to fetch pits for driver {driver_number} in session {session_key}: {exc}",
        ) from exc


@st.cache_data(ttl=600)
def _fetch_car_telemetry(
    session_key: int, driver_number: int, date_start: str, date_end: str,
) -> list[CarTelemetry]:
    _rate_limit()
    try:
        lap_start_dt = datetime.fromisoformat(date_start)
        with OpenF1Client() as f1:
            raw = f1.car_data(
                session_key=session_key,
                driver_number=driver_number,
                date=Filter(gte=date_start, lte=date_end),
            )
        result: list[CarTelemetry] = []
        for p in raw:
            if p.date is None or p.speed is None or p.rpm is None:
                continue
            t = (p.date - lap_start_dt).total_seconds()
            result.append({
                "t": t,
                "speed": p.speed,
                "rpm": p.rpm,
                "throttle": p.throttle or 0,
                "brake": p.brake or 0,
                "n_gear": p.n_gear or 0,
                "drs": p.drs or 0,
            })
        return result
    except Exception as exc:
        raise F1DataError(
            f"Failed to fetch car telemetry for driver {driver_number}: {exc}",
        ) from exc


@st.cache_data(ttl=600)
def _fetch_location(
    session_key: int, driver_number: int, date_start: str, date_end: str,
) -> list[LocationPoint]:
    _rate_limit()
    try:
        lap_start_dt = datetime.fromisoformat(date_start)
        with OpenF1Client() as f1:
            raw = f1.location(
                session_key=session_key,
                driver_number=driver_number,
                date=Filter(gte=date_start, lte=date_end),
            )
        result: list[LocationPoint] = []
        for p in raw:
            if p.date is None or p.x is None or p.y is None or p.z is None:
                continue
            t = (p.date - lap_start_dt).total_seconds()
            result.append({"t": t, "x": p.x, "y": p.y, "z": p.z})
        return result
    except Exception as exc:
        raise F1DataError(
            f"Failed to fetch location for driver {driver_number}: {exc}",
        ) from exc


# ── Repository class ─────────────────────────────────────────────────────────


class OpenF1Repository(F1DataRepository):
    """OpenF1 API data repository."""

    @log_api_call
    def get_meetings(self, year: int) -> list[MeetingData]:
        return _fetch_meetings(year)

    @log_api_call
    def get_sessions(self, meeting_key: int | str) -> list[SessionData]:
        return _fetch_sessions(int(meeting_key))

    @log_api_call
    def get_drivers(self, session_key: int | str) -> list[DriverInfo]:
        return _fetch_drivers(int(session_key))

    @log_api_call
    def get_laps(self, session_key: int | str, driver_number: int) -> list[LapData]:
        return _fetch_laps(int(session_key), driver_number)

    @log_api_call
    def get_all_laps(self, session_key: int | str) -> list[LapData]:
        return _fetch_all_laps(int(session_key))

    @log_api_call
    def get_stints(self, session_key: int | str, driver_number: int) -> list[StintData]:
        return _fetch_stints(int(session_key), driver_number)

    @log_api_call
    def get_pits(self, session_key: int | str, driver_number: int) -> list[PitData]:
        return _fetch_pits(int(session_key), driver_number)

    @log_api_call
    def get_weather(self, session_key: int | str) -> list[WeatherData]:
        return _fetch_weather(int(session_key))

    @log_api_call
    def get_car_telemetry(
        self, session_key: int | str, driver_number: int, date_start: str, date_end: str,
    ) -> list[CarTelemetry]:
        return _fetch_car_telemetry(int(session_key), driver_number, date_start, date_end)

    @log_api_call
    def get_location(
        self, session_key: int | str, driver_number: int, date_start: str, date_end: str,
    ) -> list[LocationPoint]:
        return _fetch_location(int(session_key), driver_number, date_start, date_end)
