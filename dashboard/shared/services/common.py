"""Shared pure functions for the service layer (no Streamlit dependency)."""

from __future__ import annotations

import re
import statistics

from ..constants import COMPARISON_COLORS, F1_RED

_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{3,8}$")


def filter_valid_laps(laps: list[dict]) -> list[dict]:
    """Return laps with non-None lap_duration."""
    return [lap for lap in laps if lap.get("lap_duration") is not None]


def filter_clean_laps(laps: list[dict]) -> list[dict]:
    """Return valid laps that are not pit-out laps."""
    return [
        lap for lap in laps
        if lap.get("lap_duration") is not None and not lap.get("is_pit_out_lap")
    ]


def split_clean_and_pit_out(
    valid_laps: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Split valid laps into (clean, pit_out) lists."""
    clean = [lap for lap in valid_laps if not lap.get("is_pit_out_lap")]
    pit_out = [lap for lap in valid_laps if lap.get("is_pit_out_lap")]
    return clean, pit_out


def compute_session_best(all_laps: list[dict]) -> float | None:
    """Return the fastest lap_duration across all laps, or None."""
    valid = filter_valid_laps(all_laps)
    return min((lap["lap_duration"] for lap in valid), default=None)


def compute_session_median(all_laps: list[dict]) -> float | None:
    """Return the median lap time of clean laps across the session."""
    durations = [
        lap["lap_duration"] for lap in all_laps
        if lap.get("lap_duration") is not None and not lap.get("is_pit_out_lap")
    ]
    return statistics.median(durations) if durations else None


def compute_avg_lap(valid_laps: list[dict]) -> float | None:
    """Return the mean lap time of clean (non-pit-out) valid laps."""
    clean_durations = [
        lap["lap_duration"] for lap in valid_laps
        if not lap.get("is_pit_out_lap")
    ]
    return statistics.mean(clean_durations) if clean_durations else None


def normalize_team_color(team_colour: str | None) -> str:
    """Return a validated hex color string with '#' prefix, defaulting to F1_RED."""
    if team_colour:
        candidate = f"#{team_colour}"
        if _HEX_COLOR_RE.match(candidate):
            return candidate
    return F1_RED


def assign_driver_colors(driver_list: list[dict]) -> dict[int, str]:
    """Assign a unique color to each driver, handling teammate collisions."""
    colors: dict[int, str] = {}
    used_colors: set[str] = set()
    fallback_idx = 0

    for d in driver_list:
        raw = f"#{d['team_colour']}" if d.get("team_colour") else F1_RED
        color = raw.upper()

        if color in used_colors:
            found = False
            while fallback_idx < len(COMPARISON_COLORS):
                candidate = COMPARISON_COLORS[fallback_idx].upper()
                fallback_idx += 1
                if candidate not in used_colors:
                    color = candidate
                    found = True
                    break
            if not found:
                dn = d.get("driver_number", 0)
                color = f"#{abs(hash(str(dn))) % 0xFFFFFF:06X}"

        used_colors.add(color)
        colors[d["driver_number"]] = color

    return colors


def compute_speed_stats(
    laps: list[dict],
    fields: list[tuple[str, str]],
) -> dict[str, list[float]]:
    """Compute per-zone speed averages and maxes.

    Returns dict with keys 'avgs', 'maxes' — each a list parallel to *fields*.
    """
    avgs: list[float] = []
    maxes: list[float] = []
    for field, _ in fields:
        vals = [lap[field] for lap in laps if lap.get(field) is not None]
        avgs.append(statistics.mean(vals) if vals else 0)
        maxes.append(max(vals) if vals else 0)
    return {"avgs": avgs, "maxes": maxes}


def compute_ideal_lap(laps: list[dict]) -> float | None:
    """Return best S1 + best S2 + best S3 across all laps, or None."""
    s1_vals = [lap["duration_sector_1"] for lap in laps if lap.get("duration_sector_1") is not None]
    s2_vals = [lap["duration_sector_2"] for lap in laps if lap.get("duration_sector_2") is not None]
    s3_vals = [lap["duration_sector_3"] for lap in laps if lap.get("duration_sector_3") is not None]
    if s1_vals and s2_vals and s3_vals:
        return min(s1_vals) + min(s2_vals) + min(s3_vals)
    return None
