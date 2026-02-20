"""Multi-driver comparison service — business logic extracted from 2_Driver_Comparison.py."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..data.base import F1DataRepository
from ..data.errors import F1DataError
from ..data.types import CarTelemetry, LocationPoint
from ..api_logging import log_service_call
from .stint_helpers import summarise_stints_with_sectors
from ..formatters import format_delta, format_lap_time
from .common import compute_ideal_lap, compute_session_best, filter_valid_laps


@dataclass(frozen=True)
class DriverBestLap:
    acronym: str
    best_lap: float | None
    ideal_lap: float | None
    delta: str | None


@dataclass(frozen=True)
class StintInsights:
    fastest_avg: tuple[str, float, str]
    most_consistent: tuple[str, float, str]
    best_ideal: tuple[str, float, str] | None
    best_sectors: dict[str, tuple[str, float]]


@dataclass(frozen=True)
class SectorComparisonEntry:
    acronym: str
    s1: float
    s2: float
    s3: float
    total: float
    color: str


@dataclass(frozen=True)
class TelemetryPoint:
    t: float
    value: float


@dataclass(frozen=True)
class DriverTelemetryTrace:
    acronym: str
    color: str
    points: tuple[TelemetryPoint, ...]


@dataclass(frozen=True)
class DriverPosition:
    acronym: str
    x: float
    y: float


@dataclass(frozen=True)
class TrackMapFrame:
    t: float
    driver_positions: tuple[DriverPosition, ...]


@dataclass(frozen=True)
class TrackMapData:
    track_x: tuple[float, ...]
    track_y: tuple[float, ...]
    frames: tuple[TrackMapFrame, ...]
    driver_colors: dict[str, str]
    lap_duration: float
    frame_interval_ms: int


def _estimate_stint_temperature(
    weather: list[dict],
    lap_start: int,
    lap_end: int,
    total_laps: int,
) -> float | None:
    """Estimate average track temperature during a stint.

    Maps the stint's lap range proportionally onto the session timeline,
    then averages weather samples in that time window.  Falls back to the
    nearest sample when the window contains none.
    """
    if not weather or total_laps < 1:
        return None

    timestamps = []
    for w in weather:
        try:
            timestamps.append((datetime.fromisoformat(w["timestamp"]), w["track_temperature"]))
        except (KeyError, ValueError):
            continue

    if not timestamps:
        return None

    timestamps.sort(key=lambda t: t[0])
    session_start = timestamps[0][0]
    session_end = timestamps[-1][0]
    session_duration = (session_end - session_start).total_seconds()

    if session_duration <= 0:
        return timestamps[0][1]

    # Map stint lap range to proportional time window
    frac_start = (lap_start - 1) / total_laps
    frac_end = lap_end / total_laps
    window_start = session_start.timestamp() + frac_start * session_duration
    window_end = session_start.timestamp() + frac_end * session_duration

    # Collect samples within the window
    in_window = [
        temp for ts, temp in timestamps
        if window_start <= ts.timestamp() <= window_end
    ]

    if in_window:
        return sum(in_window) / len(in_window)

    # Fallback: nearest sample to window midpoint
    midpoint = (window_start + window_end) / 2
    nearest = min(timestamps, key=lambda t: abs(t[0].timestamp() - midpoint))
    return nearest[1]


class DriverComparisonService:
    """Encapsulates all business logic for multi-driver comparison."""

    def __init__(self, repo: F1DataRepository) -> None:
        self._repo = repo

    @log_service_call
    def fetch_comparison_data(
        self,
        session_key: int | str,
        driver_numbers: list[int],
    ) -> tuple[dict[int, dict], list[dict], list[dict]]:
        """Fetch laps, stints, and weather for each driver.

        Returns (per_driver_data, all_laps, weather) where per_driver_data
        maps driver_number -> {"laps": [...], "stints": [...]}.
        Weather is an empty list if unavailable.
        """
        all_laps = self._repo.get_all_laps(session_key)

        per_driver: dict[int, dict] = {}
        for dn in driver_numbers:
            d_laps = self._repo.get_laps(session_key, dn)
            d_stints = self._repo.get_stints(session_key, dn)
            per_driver[dn] = {"laps": d_laps, "stints": d_stints}

        try:
            weather = self._repo.get_weather(session_key)
        except F1DataError:
            weather = []

        return per_driver, all_laps, weather

    @log_service_call
    def compute_best_laps(
        self,
        driver_data: dict[int, dict],
        all_laps: list[dict],
        drivers: list[dict],
    ) -> list[DriverBestLap]:
        """Compute best lap and ideal lap for each selected driver."""
        session_best = compute_session_best(all_laps)
        results: list[DriverBestLap] = []

        for d in drivers:
            dn = d["driver_number"]
            d_laps = driver_data[dn]["laps"]
            valid = filter_valid_laps(d_laps)
            best = min((lap["lap_duration"] for lap in valid), default=None)
            ideal = compute_ideal_lap(d_laps)

            results.append(DriverBestLap(
                acronym=d.get("name_acronym", "???"),
                best_lap=best,
                ideal_lap=ideal,
                delta=format_delta(best, session_best),
            ))

        return results

    @log_service_call
    def compute_stint_comparison(
        self,
        driver_data: dict[int, dict],
        drivers: list[dict],
        driver_colors: dict[int, str],
        is_practice: bool,
        weather: list[dict] | None = None,
    ) -> tuple[list[dict], list[dict], StintInsights | None]:
        """Compute stint comparison table rows, raw data, and insights.

        Returns (table_rows, raw_data, insights_or_none).
        """
        # Compute total laps across all drivers for proportional mapping
        total_laps = 0
        if weather:
            for d in drivers:
                dn = d["driver_number"]
                for stint in driver_data[dn]["stints"]:
                    lap_end = stint.get("lap_end", 0)
                    if lap_end > total_laps:
                        total_laps = lap_end

        table_rows: list[dict] = []
        raw_data: list[dict] = []

        for d in drivers:
            dn = d["driver_number"]
            acronym = d.get("name_acronym", "???")
            summaries = summarise_stints_with_sectors(
                driver_data[dn]["laps"],
                driver_data[dn]["stints"],
            )

            if is_practice:
                consistent = [
                    s for s in summaries
                    if s["num_laps"] > 5 and s["std_dev"] < 2.0
                ]
            else:
                consistent = [s for s in summaries if s["num_laps"] > 5]
            consistent.sort(key=lambda s: s["avg_time"])
            top = consistent if not is_practice else consistent[:3]

            for s in top:
                best_s1 = s["best_sector_1"]
                best_s2 = s["best_sector_2"]
                best_s3 = s["best_sector_3"]
                ideal = (
                    (best_s1 + best_s2 + best_s3)
                    if best_s1 is not None and best_s2 is not None and best_s3 is not None
                    else None
                )
                row: dict = {
                    "Driver": acronym,
                    "Compound": s["compound"],
                    "Avg Time": format_lap_time(s["avg_time"]),
                    "Best Time": format_lap_time(s["best_time"]),
                    "Ideal": format_lap_time(ideal),
                    "Laps": s["num_laps"],
                    "Avg S1": format_lap_time(s["avg_sector_1"]),
                    "Avg S2": format_lap_time(s["avg_sector_2"]),
                    "Avg S3": format_lap_time(s["avg_sector_3"]),
                    "Best S1": format_lap_time(best_s1),
                    "Best S2": format_lap_time(best_s2),
                    "Best S3": format_lap_time(best_s3),
                    "Std Dev": f"{s['std_dev']:.3f}s",
                }

                if weather and total_laps > 0:
                    temp = _estimate_stint_temperature(
                        weather, s["lap_start"], s["lap_end"], total_laps,
                    )
                    row["Track Temp"] = f"{temp:.1f}°C" if temp is not None else "\u2014"

                table_rows.append(row)
                raw_data.append({
                    "driver": acronym,
                    "compound": s["compound"],
                    "avg_time": s["avg_time"],
                    "best_time": s["best_time"],
                    "ideal": ideal,
                    "std_dev": s["std_dev"],
                    "best_s1": best_s1,
                    "best_s2": best_s2,
                    "best_s3": best_s3,
                })

        insights = self._compute_insights(raw_data) if raw_data else None
        return table_rows, raw_data, insights

    @staticmethod
    def _compute_insights(raw_data: list[dict]) -> StintInsights:
        """Derive key insights from stint raw data."""
        fastest_avg = min(raw_data, key=lambda r: r["avg_time"])
        most_consistent = min(raw_data, key=lambda r: r["std_dev"])

        ideals = [r for r in raw_data if r["ideal"] is not None]
        best_ideal: tuple[str, float, str] | None = None
        if ideals:
            bi = min(ideals, key=lambda r: r["ideal"])
            best_ideal = (bi["driver"], bi["ideal"], bi["compound"])

        best_sectors: dict[str, tuple[str, float]] = {}
        for sector_num, key in [("S1", "best_s1"), ("S2", "best_s2"), ("S3", "best_s3")]:
            sector_rows = [r for r in raw_data if r[key] is not None]
            if sector_rows:
                best = min(sector_rows, key=lambda r: r[key])
                best_sectors[sector_num] = (best["driver"], best[key])

        return StintInsights(
            fastest_avg=(fastest_avg["driver"], fastest_avg["avg_time"], fastest_avg["compound"]),
            most_consistent=(most_consistent["driver"], most_consistent["std_dev"], most_consistent["compound"]),
            best_ideal=best_ideal,
            best_sectors=best_sectors,
        )

    @log_service_call
    def compute_speed_traps(
        self,
        driver_data: dict[int, dict],
        all_laps: list[dict],
        all_drivers: list[dict],
        selected_drivers: list[dict],
        driver_colors: dict[int, str],
    ) -> tuple[list[dict], dict[str, float], dict[str, str]]:
        """Compute speed trap data for the comparison chart.

        Returns (driver_entries, session_max_speeds, session_speed_holders).
        Each driver_entry has: acronym, color, zone_labels, max_speeds.
        """
        speed_zones = [
            ("i1_speed", "I1"),
            ("i2_speed", "I2"),
            ("st_speed", "ST"),
        ]

        driver_by_number: dict[int, dict] = {
            d["driver_number"]: d for d in all_drivers if d.get("driver_number")
        }

        session_max_speeds: dict[str, float] = {}
        session_speed_holder: dict[str, str] = {}
        for field, label in speed_zones:
            zone_laps = [lap for lap in all_laps if lap.get(field) is not None]
            if zone_laps:
                best_lap = max(zone_laps, key=lambda lap: lap[field])
                session_max_speeds[label] = best_lap[field]
                holder = driver_by_number.get(best_lap.get("driver_number", 0), {})
                holder_name = holder.get("name_acronym", "???")
                holder_team = holder.get("team_name", "")
                session_speed_holder[label] = (
                    f"{holder_name} ({holder_team})" if holder_team else holder_name
                )

        entries: list[dict] = []
        for d in selected_drivers:
            dn = d["driver_number"]
            d_laps = driver_data[dn]["laps"]
            max_speeds: list[float] = []
            zone_labels: list[str] = []

            for field, label in speed_zones:
                vals = [lap[field] for lap in d_laps if lap.get(field) is not None]
                max_speeds.append(max(vals) if vals else 0)
                zone_labels.append(label)

            entries.append({
                "acronym": d.get("name_acronym", "???"),
                "color": driver_colors[dn],
                "zone_labels": zone_labels,
                "max_speeds": max_speeds,
            })

        return entries, session_max_speeds, session_speed_holder

    @log_service_call
    def compute_sector_comparison(
        self,
        driver_data: dict[int, dict],
        drivers: list[dict],
        driver_colors: dict[int, str],
    ) -> list[SectorComparisonEntry]:
        """Compute sector time comparison from each driver's fastest lap."""
        results: list[SectorComparisonEntry] = []

        for d in drivers:
            dn = d["driver_number"]
            d_laps = driver_data[dn]["laps"]

            sector_laps = [
                lap for lap in d_laps
                if (
                    lap.get("lap_duration") is not None
                    and lap.get("duration_sector_1") is not None
                    and lap.get("duration_sector_2") is not None
                    and lap.get("duration_sector_3") is not None
                    and not lap.get("is_pit_out_lap")
                )
            ]

            if sector_laps:
                fastest = min(sector_laps, key=lambda lap: lap["lap_duration"])
                s1 = fastest["duration_sector_1"]
                s2 = fastest["duration_sector_2"]
                s3 = fastest["duration_sector_3"]
                results.append(SectorComparisonEntry(
                    acronym=d.get("name_acronym", "???"),
                    s1=s1,
                    s2=s2,
                    s3=s3,
                    total=s1 + s2 + s3,
                    color=driver_colors[dn],
                ))

        return results

    @log_service_call
    def fetch_telemetry_for_best_laps(
        self,
        session_key: int | str,
        driver_data: dict[int, dict],
        drivers: list[dict],
        driver_colors: dict[int, str],
    ) -> dict[int, dict]:
        """Fetch car telemetry and location for each driver's best lap.

        Returns a dict mapping driver_number -> {"car": [...], "location": [...], "acronym": str, "color": str}.
        Drivers whose telemetry is unavailable are silently skipped.
        """
        result: dict[int, dict] = {}

        for d in drivers:
            dn = d["driver_number"]
            acronym = d.get("name_acronym", "???")
            color = driver_colors[dn]
            d_laps = driver_data[dn]["laps"]

            # Find best lap with date_start
            valid = [
                lap for lap in d_laps
                if lap.get("lap_duration") is not None
                and not lap.get("is_pit_out_lap")
                and lap.get("date_start") is not None
            ]
            if not valid:
                continue

            best_lap = min(valid, key=lambda lap: lap["lap_duration"])
            date_start = best_lap["date_start"]
            lap_duration = best_lap["lap_duration"]

            # Compute date_end from date_start + lap_duration
            start_dt = datetime.fromisoformat(date_start)
            end_dt = start_dt + timedelta(seconds=lap_duration)
            date_end = end_dt.isoformat()

            try:
                car = self._repo.get_car_telemetry(session_key, dn, date_start, date_end)
            except F1DataError:
                car = []

            try:
                location = self._repo.get_location(session_key, dn, date_start, date_end)
            except F1DataError:
                location = []

            result[dn] = {
                "car": car,
                "location": location,
                "acronym": acronym,
                "color": color,
            }

        return result

    @staticmethod
    def compute_speed_trace(
        telemetry_data: dict[int, dict],
    ) -> list[DriverTelemetryTrace]:
        """Extract speed vs time traces from telemetry data."""
        traces: list[DriverTelemetryTrace] = []
        for dn, data in telemetry_data.items():
            car: list[CarTelemetry] = data["car"]
            if not car:
                continue
            points = tuple(
                TelemetryPoint(t=p["t"], value=float(p["speed"]))
                for p in car
            )
            traces.append(DriverTelemetryTrace(
                acronym=data["acronym"],
                color=data["color"],
                points=points,
            ))
        return traces

    @staticmethod
    def compute_rpm_trace(
        telemetry_data: dict[int, dict],
    ) -> list[DriverTelemetryTrace]:
        """Extract RPM vs time traces from telemetry data."""
        traces: list[DriverTelemetryTrace] = []
        for dn, data in telemetry_data.items():
            car: list[CarTelemetry] = data["car"]
            if not car:
                continue
            points = tuple(
                TelemetryPoint(t=p["t"], value=float(p["rpm"]))
                for p in car
            )
            traces.append(DriverTelemetryTrace(
                acronym=data["acronym"],
                color=data["color"],
                points=points,
            ))
        return traces

    @staticmethod
    def compute_track_map(
        telemetry_data: dict[int, dict],
    ) -> TrackMapData | None:
        """Build track map animation data from location points.

        Uses the first driver's full location trace as the track outline,
        then creates animation frames by aligning all drivers to common time points.
        """
        # Find a driver with location data for the track outline
        outline_locations: list[LocationPoint] | None = None
        for data in telemetry_data.values():
            if data["location"]:
                outline_locations = data["location"]
                break

        if outline_locations is None:
            return None

        track_x = tuple(p["x"] for p in outline_locations)
        track_y = tuple(p["y"] for p in outline_locations)

        # Collect all unique time points from all drivers
        all_times: set[float] = set()
        for data in telemetry_data.values():
            for p in data["location"]:
                all_times.add(round(p["t"], 2))

        if not all_times:
            return None

        sorted_times = sorted(all_times)

        # Compute max lap duration across drivers
        max_duration = max(
            (p["t"] for data in telemetry_data.values() for p in data["location"]),
            default=0.0,
        )

        # Build driver colors map
        driver_colors: dict[str, str] = {}
        for data in telemetry_data.values():
            driver_colors[data["acronym"]] = data["color"]

        # Build frames at a fixed real-time interval (250ms)
        frame_interval_s = 0.25
        frame_interval_ms = int(frame_interval_s * 1000)
        sampled_times = []
        t = 0.0
        while t <= max_duration:
            sampled_times.append(t)
            t += frame_interval_s

        # Pre-sort each driver's location by time for efficient nearest lookup
        driver_sorted_locs: list[tuple[dict, list[LocationPoint]]] = []
        for data in telemetry_data.values():
            if data["location"]:
                loc_sorted = sorted(data["location"], key=lambda p: p["t"])
                driver_sorted_locs.append((data, loc_sorted))

        frames: list[TrackMapFrame] = []
        for t in sampled_times:
            positions: list[DriverPosition] = []
            for data, loc in driver_sorted_locs:
                # Binary search for nearest point
                nearest = min(loc, key=lambda p: abs(p["t"] - t))
                if abs(nearest["t"] - t) <= 0.5:
                    positions.append(DriverPosition(
                        acronym=data["acronym"],
                        x=nearest["x"],
                        y=nearest["y"],
                    ))
            frames.append(TrackMapFrame(t=t, driver_positions=tuple(positions)))

        return TrackMapData(
            track_x=track_x,
            track_y=track_y,
            frames=tuple(frames),
            driver_colors=driver_colors,
            lap_duration=max_duration,
            frame_interval_ms=frame_interval_ms,
        )
