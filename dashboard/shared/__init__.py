"""Shared dashboard utilities."""

# --- Constants & formatting ---
from .constants import (
    COMPARISON_COLORS,
    COMPOUND_COLORS,
    F1_RED,
    PLOTLY_LAYOUT_DEFAULTS,
    PRACTICE_SESSION_TYPES,
)
from .formatters import format_delta, format_lap_time

# --- Data layer ---
from .data import F1DataError, get_repository
from .data.source import DataSource, fastf1_available, get_active_source

# --- Service layer ---
from .services import (
    DriverComparisonService,
    DriverPerformanceService,
    assign_driver_colors,
    normalize_team_color,
)
from .services.stint_helpers import get_compound_for_lap, summarise_stints, summarise_stints_with_sectors

# --- UI components ---
from .sidebar import SessionSelection, render_session_sidebar

__all__ = [
    "COMPARISON_COLORS",
    "COMPOUND_COLORS",
    "DataSource",
    "DriverComparisonService",
    "DriverPerformanceService",
    "F1DataError",
    "F1_RED",
    "PLOTLY_LAYOUT_DEFAULTS",
    "PRACTICE_SESSION_TYPES",
    "SessionSelection",
    "assign_driver_colors",
    "fastf1_available",
    "format_delta",
    "format_lap_time",
    "get_active_source",
    "get_compound_for_lap",
    "get_repository",
    "normalize_team_color",
    "render_session_sidebar",
    "summarise_stints",
    "summarise_stints_with_sectors",
]
