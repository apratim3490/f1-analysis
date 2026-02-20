"""FastF1 data repository implementation."""

from __future__ import annotations

import streamlit as st

from .base import F1DataRepository
from .errors import F1DataError
from ..api_logging import log_api_call
from .types import CarTelemetry, DriverInfo, LapData, LocationPoint, MeetingData, PitData, SessionData, StintData, WeatherData

# ── Helpers ──────────────────────────────────────────────────────────────────


def _td_to_seconds(td: object) -> float | None:
    """Convert a pandas Timedelta to float seconds, or None if NaT."""
    import pandas as pd

    if pd.isna(td):
        return None
    if isinstance(td, pd.Timedelta):
        return td.total_seconds()
    return None


def _safe_float(value: object) -> float | None:
    """Convert a numeric value to float, returning None for NaN/None."""
    import pandas as pd

    if value is None or pd.isna(value):
        return None
    return float(value)


def _safe_int(value: object) -> int | None:
    """Convert a numeric value to int, returning None for NaN/None."""
    import pandas as pd

    if value is None or pd.isna(value):
        return None
    return int(value)


def _normalize_team_colour(colour: object) -> str | None:
    """Normalize FastF1 team colour to hex string without '#' prefix."""
    import pandas as pd

    if colour is None or pd.isna(colour):
        return None
    s = str(colour).lstrip("#")
    return s if s else None


def _is_nat(value: object) -> bool:
    """Return True if value is NaT or NaN."""
    import pandas as pd

    return pd.isna(value)


def _format_lap_start_date(value: object) -> str | None:
    """Convert a FastF1 LapStartDate (pandas Timestamp) to ISO 8601 string."""
    import pandas as pd

    if value is None or pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return None


def _normalize_lap(row: object) -> LapData | None:
    """Convert a single FastF1 lap row to the shared lap dict contract.

    Returns None if lap_number or driver_number is missing.
    """
    lap_number = _safe_int(row.get("LapNumber"))  # type: ignore[union-attr]
    driver_number = _safe_int(row.get("DriverNumber"))  # type: ignore[union-attr]
    if lap_number is None or driver_number is None:
        return None
    return {
        "lap_number": lap_number,
        "lap_duration": _td_to_seconds(row.get("LapTime")),  # type: ignore[union-attr]
        "is_pit_out_lap": row.get("PitOutTime") is not None and not _is_nat(row.get("PitOutTime")),  # type: ignore[union-attr]
        "duration_sector_1": _td_to_seconds(row.get("Sector1Time")),  # type: ignore[union-attr]
        "duration_sector_2": _td_to_seconds(row.get("Sector2Time")),  # type: ignore[union-attr]
        "duration_sector_3": _td_to_seconds(row.get("Sector3Time")),  # type: ignore[union-attr]
        "i1_speed": _safe_float(row.get("SpeedI1")),  # type: ignore[union-attr]
        "i2_speed": _safe_float(row.get("SpeedI2")),  # type: ignore[union-attr]
        "st_speed": _safe_float(row.get("SpeedST")),  # type: ignore[union-attr]
        "driver_number": driver_number,
        "date_start": _format_lap_start_date(row.get("LapStartDate")),  # type: ignore[union-attr]
    }


# ── Key parsing ──────────────────────────────────────────────────────────────


def _parse_session_key(session_key: str) -> tuple[int, str, str, int | None]:
    """Parse a composite FastF1 session key.

    Supports two formats:
    - 'year|event|session' — unique event name (occurrence=None)
    - 'year|event|occurrence|session' — disambiguated duplicate (1-indexed)
    """
    parts = session_key.split("|")
    if len(parts) == 3:
        return int(parts[0]), parts[1], parts[2], None
    if len(parts) == 4:
        return int(parts[0]), parts[1], parts[3], int(parts[2])
    raise F1DataError(
        f"Invalid FastF1 session key format: {session_key!r}",
    )


def _parse_meeting_key(meeting_key: str) -> tuple[int, str, int | None]:
    """Parse a composite FastF1 meeting key.

    Supports two formats:
    - 'year|event_name' — unique event name (occurrence=None)
    - 'year|event_name|occurrence' — disambiguated duplicate (1-indexed)
    """
    parts = meeting_key.split("|")
    if len(parts) == 2:
        return int(parts[0]), parts[1], None
    if len(parts) == 3:
        return int(parts[0]), parts[1], int(parts[2])
    raise F1DataError(
        f"Invalid FastF1 meeting key format: {meeting_key!r}",
    )


# ── Session loading (cached) ────────────────────────────────────────────────


def _get_event(year: int, event_name: str, occurrence: int | None = None) -> object:
    """Look up an event by name from the schedule.

    When *occurrence* is given (1-indexed), returns the Nth event with that name.
    """
    import fastf1

    schedule = fastf1.get_event_schedule(year, include_testing=True)
    matches = schedule[schedule["EventName"] == event_name]
    if matches.empty:
        raise F1DataError(f"No event named {event_name!r} in {year}")
    if occurrence is not None:
        if occurrence < 1 or occurrence > len(matches):
            raise F1DataError(
                f"Occurrence {occurrence} out of range for {event_name!r} (found {len(matches)})",
            )
        return matches.iloc[occurrence - 1]
    return matches.iloc[0]


@st.cache_resource(show_spinner="Loading FastF1 session data...")
def _load_fastf1_session(
    year: int, event_name: str, session_name: str, occurrence: int | None = None,
) -> object:
    """Load and cache a FastF1 session object."""
    event_row = _get_event(year, event_name, occurrence)
    session = event_row.get_session(session_name)
    session.load()
    return session


# ── Session column mapping ───────────────────────────────────────────────────

_SESSION_COLUMNS = [
    ("Session1", "Session1Date"),
    ("Session2", "Session2Date"),
    ("Session3", "Session3Date"),
    ("Session4", "Session4Date"),
    ("Session5", "Session5Date"),
]

_SESSION_TYPE_MAP = {
    "Practice 1": "Practice",
    "Practice 2": "Practice",
    "Practice 3": "Practice",
    "Sprint Shootout": "Qualifying",
    "Sprint Qualifying": "Qualifying",
    "Sprint": "Race",
    "Qualifying": "Qualifying",
    "Race": "Race",
}


# ── Telemetry helpers ───────────────────────────────────────────────────────


def _find_lap_by_start_date(session: object, driver_number: int, date_start: str) -> object | None:
    """Find a FastF1 lap row matching the given driver and start date."""
    import pandas as pd

    laps = session.laps  # type: ignore[attr-defined]
    driver_laps = laps[laps["DriverNumber"] == str(driver_number)]

    if driver_laps.empty:
        return None

    target_ts = pd.Timestamp(date_start)
    for _, row in driver_laps.iterrows():
        lap_start = row.get("LapStartDate")
        if lap_start is not None and not pd.isna(lap_start):
            if pd.Timestamp(lap_start) == target_ts:
                return row

    return None


@st.cache_data(ttl=600)
def _fetch_fastf1_telemetry(
    session_key: str, driver_number: int, date_start: str, mode: str,
) -> list:
    """Fetch telemetry from FastF1 for a specific lap.

    Args:
        mode: "car" for CarTelemetry, "location" for LocationPoint.
    """
    import pandas as pd

    try:
        year, event, sess, occ = _parse_session_key(session_key)
        session = _load_fastf1_session(year, event, sess, occ)
        lap = _find_lap_by_start_date(session, driver_number, date_start)

        if lap is None:
            return []

        telemetry = lap.get_telemetry()  # type: ignore[union-attr]
        if telemetry is None or telemetry.empty:
            return []

        # Time column resets to 0 at first sample — convert to seconds
        result: list = []
        for _, row in telemetry.iterrows():
            time_val = row.get("Time")
            if time_val is None or pd.isna(time_val):
                continue
            t = pd.Timedelta(time_val).total_seconds()

            if mode == "car":
                speed = row.get("Speed")
                rpm = row.get("RPM")
                if speed is None or pd.isna(speed) or rpm is None or pd.isna(rpm):
                    continue
                result.append({
                    "t": t,
                    "speed": int(speed),
                    "rpm": int(rpm),
                    "throttle": int(row.get("Throttle", 0) or 0),
                    "brake": int(row.get("Brake", 0) or 0),
                    "n_gear": int(row.get("nGear", 0) or 0),
                    "drs": int(row.get("DRS", 0) or 0),
                })
            elif mode == "location":
                x = row.get("X")
                y = row.get("Y")
                z = row.get("Z")
                if x is None or pd.isna(x) or y is None or pd.isna(y):
                    continue
                result.append({
                    "t": t,
                    "x": float(x),
                    "y": float(y),
                    "z": float(z) if z is not None and not pd.isna(z) else 0.0,
                })

        return result
    except F1DataError:
        raise
    except Exception as exc:
        raise F1DataError(
            f"Failed to fetch {mode} telemetry for driver {driver_number}: {exc}",
        ) from exc


# ── Repository class ─────────────────────────────────────────────────────────


class FastF1Repository(F1DataRepository):
    """FastF1 data repository."""

    @log_api_call
    def get_meetings(self, year: int) -> list[MeetingData]:
        try:
            import fastf1
            import pandas as pd

            schedule = fastf1.get_event_schedule(year, include_testing=True)

            # Detect duplicate event names (e.g. multiple Pre-Season Testing weeks)
            name_counts: dict[str, int] = {}
            for _, row in schedule.iterrows():
                name = row.get("EventName")
                if name:
                    name_counts[str(name)] = name_counts.get(str(name), 0) + 1

            name_seen: dict[str, int] = {}
            events: list[MeetingData] = []
            for _, row in schedule.iterrows():
                name = row.get("EventName")
                if not name:
                    continue
                name_str = str(name)
                event_date = row.get("EventDate")

                # Disambiguate duplicate names with a date suffix
                if name_counts.get(name_str, 1) > 1:
                    idx = name_seen.get(name_str, 0) + 1
                    name_seen[name_str] = idx
                    if event_date is not None and not pd.isna(event_date):
                        date_str = pd.Timestamp(event_date).strftime("%b %d")
                        display_name = f"{name_str} (Week {idx}, {date_str})"
                    else:
                        display_name = f"{name_str} (Week {idx})"
                    meeting_key = f"{year}|{name_str}|{idx}"
                else:
                    display_name = name_str
                    meeting_key = f"{year}|{name_str}"

                events.append({
                    "meeting_name": display_name,
                    "meeting_key": meeting_key,
                })
            return events
        except Exception as exc:
            raise F1DataError(f"Failed to fetch events for {year}: {exc}") from exc

    @log_api_call
    def get_sessions(self, meeting_key: int | str) -> list[SessionData]:
        try:
            year, event_name, occurrence = _parse_meeting_key(str(meeting_key))
            event = _get_event(year, event_name, occurrence)

            sessions: list[SessionData] = []
            for col, _date_col in _SESSION_COLUMNS:
                name = event.get(col)  # type: ignore[union-attr]
                if not name or str(name).strip() in ("", "None"):
                    continue
                name_str = str(name)
                # Include occurrence in session key when present
                if occurrence is not None:
                    session_key = f"{year}|{event_name}|{occurrence}|{name_str}"
                else:
                    session_key = f"{year}|{event_name}|{name_str}"
                sessions.append({
                    "session_name": name_str,
                    "session_key": session_key,
                    "session_type": _SESSION_TYPE_MAP.get(name_str, name_str),
                })
            return sessions
        except F1DataError:
            raise
        except Exception as exc:
            raise F1DataError(f"Failed to fetch sessions for {meeting_key}: {exc}") from exc

    @log_api_call
    def get_drivers(self, session_key: int | str) -> list[DriverInfo]:
        try:
            year, event, sess, occ = _parse_session_key(str(session_key))
            session = _load_fastf1_session(year, event, sess, occ)
            results = session.results  # type: ignore[attr-defined]

            drivers: list[DriverInfo] = []
            for _, row in results.iterrows():
                dn = row.get("DriverNumber")
                if dn is None:
                    continue
                drivers.append({
                    "driver_number": int(dn),
                    "name_acronym": str(row.get("Abbreviation", "???")),
                    "full_name": f"{row.get('FirstName', '')} {row.get('LastName', '')}".strip(),
                    "team_name": str(row.get("TeamName", "")),
                    "team_colour": _normalize_team_colour(row.get("TeamColor")),
                    "headshot_url": str(row.get("HeadshotUrl", "")) or None,
                })
            return drivers
        except F1DataError:
            raise
        except Exception as exc:
            raise F1DataError(f"Failed to fetch drivers for session {session_key}: {exc}") from exc

    @log_api_call
    def get_laps(self, session_key: int | str, driver_number: int) -> list[LapData]:
        try:
            year, event, sess, occ = _parse_session_key(str(session_key))
            session = _load_fastf1_session(year, event, sess, occ)
            laps = session.laps  # type: ignore[attr-defined]
            driver_laps = laps[laps["DriverNumber"] == str(driver_number)]
            return [lap for _, row in driver_laps.iterrows() if (lap := _normalize_lap(row)) is not None]
        except F1DataError:
            raise
        except Exception as exc:
            raise F1DataError(
                f"Failed to fetch laps for driver {driver_number} in session {session_key}: {exc}",
            ) from exc

    @log_api_call
    def get_all_laps(self, session_key: int | str) -> list[LapData]:
        try:
            year, event, sess, occ = _parse_session_key(str(session_key))
            session = _load_fastf1_session(year, event, sess, occ)
            laps = session.laps  # type: ignore[attr-defined]
            return [lap for _, row in laps.iterrows() if (lap := _normalize_lap(row)) is not None]
        except F1DataError:
            raise
        except Exception as exc:
            raise F1DataError(f"Failed to fetch all laps for session {session_key}: {exc}") from exc

    @log_api_call
    def get_stints(self, session_key: int | str, driver_number: int) -> list[StintData]:
        try:
            year, event, sess, occ = _parse_session_key(str(session_key))
            session = _load_fastf1_session(year, event, sess, occ)
            laps = session.laps  # type: ignore[attr-defined]
            driver_laps = laps[laps["DriverNumber"] == str(driver_number)]

            if driver_laps.empty:
                return []

            stints: list[StintData] = []
            for stint_num, group in driver_laps.groupby("Stint"):
                lap_numbers = group["LapNumber"].dropna().astype(int)
                if lap_numbers.empty:
                    continue

                compound = str(group["Compound"].iloc[0]) if "Compound" in group.columns else "UNKNOWN"
                tyre_life = group.get("TyreLife")
                tyre_age = (
                    int(tyre_life.iloc[0])
                    if tyre_life is not None and not tyre_life.empty and not _is_nat(tyre_life.iloc[0])
                    else 0
                )

                stints.append({
                    "stint_number": int(stint_num),
                    "lap_start": int(lap_numbers.min()),
                    "lap_end": int(lap_numbers.max()),
                    "compound": compound.upper() if compound else "UNKNOWN",
                    "tyre_age_at_start": tyre_age,
                })

            return sorted(stints, key=lambda s: s["stint_number"])
        except F1DataError:
            raise
        except Exception as exc:
            raise F1DataError(
                f"Failed to fetch stints for driver {driver_number} in session {session_key}: {exc}",
            ) from exc

    @log_api_call
    def get_weather(self, session_key: int | str) -> list[WeatherData]:
        try:
            import pandas as pd

            year, event, sess, occ = _parse_session_key(str(session_key))
            session = _load_fastf1_session(year, event, sess, occ)
            weather_df = session.weather_data  # type: ignore[attr-defined]

            if weather_df is None or weather_df.empty:
                return []

            session_start = session.date  # type: ignore[attr-defined]
            results: list[WeatherData] = []
            for _, row in weather_df.iterrows():
                track_temp = row.get("TrackTemp")
                time_offset = row.get("Time")
                if track_temp is None or pd.isna(track_temp):
                    continue
                if time_offset is None or pd.isna(time_offset):
                    continue
                abs_time = session_start + pd.Timedelta(time_offset)
                results.append({
                    "track_temperature": float(track_temp),
                    "timestamp": abs_time.isoformat(),
                })
            return results
        except F1DataError:
            raise
        except Exception as exc:
            raise F1DataError(
                f"Failed to fetch weather for session {session_key}: {exc}",
            ) from exc

    @log_api_call
    def get_pits(self, session_key: int | str, driver_number: int) -> list[PitData]:
        try:
            year, event, sess, occ = _parse_session_key(str(session_key))
            session = _load_fastf1_session(year, event, sess, occ)
            laps = session.laps  # type: ignore[attr-defined]
            driver_laps = laps[laps["DriverNumber"] == str(driver_number)]

            if driver_laps.empty:
                return []

            pits: list[PitData] = []
            for _, row in driver_laps.iterrows():
                pit_in = row.get("PitInTime")
                pit_out = row.get("PitOutTime")

                if pit_in is None or _is_nat(pit_in):
                    continue

                duration = None
                if pit_out is not None and not _is_nat(pit_out):
                    duration = _td_to_seconds(pit_out - pit_in)

                pits.append({
                    "lap_number": _safe_int(row.get("LapNumber")),
                    "pit_duration": duration,
                })

            return sorted(pits, key=lambda p: p.get("lap_number") or 0)
        except F1DataError:
            raise
        except Exception as exc:
            raise F1DataError(
                f"Failed to fetch pits for driver {driver_number} in session {session_key}: {exc}",
            ) from exc

    @log_api_call
    def get_car_telemetry(
        self, session_key: int | str, driver_number: int, date_start: str, date_end: str,
    ) -> list[CarTelemetry]:
        return _fetch_fastf1_telemetry(str(session_key), driver_number, date_start, "car")

    @log_api_call
    def get_location(
        self, session_key: int | str, driver_number: int, date_start: str, date_end: str,
    ) -> list[LocationPoint]:
        return _fetch_fastf1_telemetry(str(session_key), driver_number, date_start, "location")
