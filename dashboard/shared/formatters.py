"""Formatting helpers for the F1 dashboard."""

from __future__ import annotations


def format_lap_time(seconds: float | None) -> str:
    """Format seconds as m:ss.fff or '\u2014' if None."""
    if seconds is None:
        return "\u2014"
    mins, secs = divmod(seconds, 60)
    return f"{int(mins)}:{secs:06.3f}"


def format_delta(driver_best: float | None, session_best: float | None) -> str | None:
    """Format delta to session best as +s.fff or None."""
    if driver_best is None or session_best is None:
        return None
    delta = driver_best - session_best
    if abs(delta) < 0.0005:
        return "(session best)"
    return f"(+{delta:.3f})"
