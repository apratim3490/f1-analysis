"""Single-driver performance service — business logic extracted from app.py."""

from __future__ import annotations

from dataclasses import dataclass

from ..data.base import F1DataRepository
from ..api_logging import log_service_call
from .stint_helpers import get_compound_for_lap, summarise_stints
from .common import (
    compute_avg_lap,
    compute_session_best,
    compute_session_median,
    compute_speed_stats,
    filter_valid_laps,
    split_clean_and_pit_out,
)


@dataclass(frozen=True)
class DriverKPIs:
    total_laps: int
    best_lap: float | None
    session_best: float | None
    avg_lap: float | None
    pit_count: int | None
    best_lap_delta: str | None


@dataclass(frozen=True)
class LapProgressionData:
    clean_laps: list[dict]
    pit_out_laps: list[dict]
    session_median: float | None
    session_best: float | None
    compound_groups: dict[str, list[dict]] | None
    edge_excluded_laps: frozenset[int]


@dataclass(frozen=True)
class SectorBreakdownData:
    sector_laps: list[dict]
    compounds: list[str] | None


@dataclass(frozen=True)
class SpeedTrapData:
    categories: list[str]
    driver_avgs: list[float]
    driver_maxes: list[float]
    session_bests: list[float]
    has_data: bool


@dataclass(frozen=True)
class TireStrategyData:
    stints: list[dict]


class DriverPerformanceService:
    """Encapsulates all business logic for single-driver performance analysis."""

    def __init__(self, repo: F1DataRepository) -> None:
        self._repo = repo

    @log_service_call
    def fetch_driver_data(
        self,
        session_key: int | str,
        driver_number: int,
    ) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
        """Fetch laps, all_laps, stints, and pits for a driver."""
        laps = self._repo.get_laps(session_key, driver_number)
        all_laps = self._repo.get_all_laps(session_key)
        stints = self._repo.get_stints(session_key, driver_number)
        pits = self._repo.get_pits(session_key, driver_number)
        return laps, all_laps, stints, pits

    @log_service_call
    def compute_kpis(
        self,
        laps: list[dict],
        all_laps: list[dict],
        pits: list[dict],
        is_practice: bool,
    ) -> DriverKPIs:
        """Compute KPI metrics for a driver."""
        from ..formatters import format_delta

        valid_laps = filter_valid_laps(laps)
        best_lap = min((lap["lap_duration"] for lap in valid_laps), default=None)
        session_best = compute_session_best(all_laps)
        avg_lap = None if is_practice else compute_avg_lap(valid_laps)
        pit_count = None if is_practice else len(pits)

        return DriverKPIs(
            total_laps=len(laps),
            best_lap=best_lap,
            session_best=session_best,
            avg_lap=avg_lap,
            pit_count=pit_count,
            best_lap_delta=format_delta(best_lap, session_best),
        )

    @log_service_call
    def prepare_lap_progression(
        self,
        laps: list[dict],
        all_laps: list[dict],
        stints: list[dict],
        is_practice: bool,
    ) -> LapProgressionData:
        """Prepare data for the lap time progression chart."""
        valid_laps = filter_valid_laps(laps)
        clean_laps, pit_out_laps = split_clean_and_pit_out(valid_laps)
        session_median = compute_session_median(all_laps)
        session_best = compute_session_best(all_laps)

        compound_groups: dict[str, list[dict]] | None = None
        _excluded: set[int] = set()

        if is_practice:
            stint_summaries = summarise_stints(laps, stints)
            valid_stints = [s for s in stint_summaries if s["num_laps"] > 5]
            for s in valid_stints:
                _excluded.update(s["excluded_laps"])

            compound_groups = {}
            for lap in clean_laps:
                if lap["lap_number"] in _excluded:
                    continue
                compound = get_compound_for_lap(lap["lap_number"], stints)
                compound_groups.setdefault(compound, []).append(lap)

        return LapProgressionData(
            clean_laps=clean_laps,
            pit_out_laps=pit_out_laps,
            session_median=session_median,
            session_best=session_best,
            compound_groups=compound_groups,
            edge_excluded_laps=frozenset(_excluded),
        )

    @log_service_call
    def prepare_sector_breakdown(
        self,
        laps: list[dict],
        stints: list[dict],
        is_practice: bool,
    ) -> SectorBreakdownData:
        """Prepare data for the sector breakdown chart."""
        sector_laps = [
            lap for lap in laps
            if (
                lap.get("duration_sector_1") is not None
                and lap.get("duration_sector_2") is not None
                and lap.get("duration_sector_3") is not None
                and not lap.get("is_pit_out_lap")
            )
        ]

        compounds: list[str] | None = None
        if is_practice:
            compounds = [
                get_compound_for_lap(lap["lap_number"], stints)
                for lap in sector_laps
            ]

        return SectorBreakdownData(
            sector_laps=sector_laps,
            compounds=compounds,
        )

    @log_service_call
    def prepare_speed_traps(
        self,
        laps: list[dict],
        all_laps: list[dict],
    ) -> SpeedTrapData:
        """Prepare data for the speed trap comparison chart."""
        speed_fields = [
            ("i1_speed", "I1 Speed"),
            ("i2_speed", "I2 Speed"),
            ("st_speed", "Speed Trap"),
        ]

        driver_stats = compute_speed_stats(laps, speed_fields)
        session_stats = compute_speed_stats(all_laps, speed_fields)

        # Only include fields where the driver has data
        active_indices = [
            i for i, (field, _) in enumerate(speed_fields)
            if any(lap.get(field) is not None for lap in laps)
        ]

        if not active_indices:
            return SpeedTrapData(
                categories=[], driver_avgs=[], driver_maxes=[],
                session_bests=[], has_data=False,
            )

        categories = [speed_fields[i][1] for i in active_indices]
        driver_avgs = [driver_stats["avgs"][i] for i in active_indices]
        driver_maxes = [driver_stats["maxes"][i] for i in active_indices]
        session_bests = [session_stats["maxes"][i] for i in active_indices]

        return SpeedTrapData(
            categories=categories,
            driver_avgs=driver_avgs,
            driver_maxes=driver_maxes,
            session_bests=session_bests,
            has_data=True,
        )

    @log_service_call
    def prepare_stint_summaries(
        self,
        laps: list[dict],
        stints: list[dict],
    ) -> list[dict]:
        """Return stint summaries filtered to >5 laps."""
        all_summaries = summarise_stints(laps, stints)
        return [s for s in all_summaries if s["num_laps"] > 5]

    @log_service_call
    def get_tire_strategy(self, stints: list[dict]) -> TireStrategyData:
        """Return tire strategy data for the timeline chart."""
        return TireStrategyData(stints=stints)
