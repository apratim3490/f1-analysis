"""Service layer — business logic for the F1 dashboard."""

from .common import (
    assign_driver_colors,
    compute_avg_lap,
    compute_ideal_lap,
    compute_session_best,
    compute_session_median,
    compute_speed_stats,
    filter_clean_laps,
    filter_valid_laps,
    normalize_team_color,
    split_clean_and_pit_out,
)
from .driver_comparison import (
    DriverComparisonService,
    DriverTelemetryTrace,
    TelemetryPoint,
    TrackMapData,
)
from .driver_performance import DriverPerformanceService
from .stint_helpers import get_compound_for_lap, summarise_stints, summarise_stints_with_sectors

__all__ = [
    "DriverComparisonService",
    "DriverPerformanceService",
    "DriverTelemetryTrace",
    "TelemetryPoint",
    "TrackMapData",
    "assign_driver_colors",
    "compute_avg_lap",
    "compute_ideal_lap",
    "compute_session_best",
    "compute_session_median",
    "compute_speed_stats",
    "filter_clean_laps",
    "filter_valid_laps",
    "normalize_team_color",
    "split_clean_and_pit_out",
    "get_compound_for_lap",
    "summarise_stints",
    "summarise_stints_with_sectors",
]
