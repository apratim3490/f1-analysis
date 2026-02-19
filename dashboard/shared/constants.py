"""Shared constants for the F1 dashboard."""

from __future__ import annotations

F1_RED = "#E10600"

COMPOUND_COLORS: dict[str, str] = {
    "SOFT": "#FF3333",
    "MEDIUM": "#FFC700",
    "HARD": "#FFFFFF",
    "INTERMEDIATE": "#39B54A",
    "WET": "#0067FF",
    "UNKNOWN": "#888888",
}

PRACTICE_SESSION_TYPES = {"Practice"}

PLOTLY_LAYOUT_DEFAULTS = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#F0F0F0",
    margin=dict(l=40, r=20, t=40, b=40),
)

# Fallback colors for disambiguating teammates with the same team color
COMPARISON_COLORS: list[str] = [
    "#00D2BE",  # teal
    "#FF8700",  # orange
    "#BF00FF",  # purple
    "#FFD700",  # gold
]
