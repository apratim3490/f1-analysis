"""Data processing helpers for the F1 dashboard."""

from __future__ import annotations

import statistics


def get_compound_for_lap(lap_number: int, stints: list[dict]) -> str:
    """Look up the tire compound for a given lap number from stint data."""
    for stint in stints:
        lap_start = stint.get("lap_start")
        lap_end = stint.get("lap_end")
        if lap_start is None or lap_end is None:
            continue
        if lap_start <= lap_number <= lap_end:
            return (stint.get("compound") or "UNKNOWN").upper()
    return "UNKNOWN"


def _compute_stint_clean_laps(
    laps: list[dict],
    stint: dict,
    threshold: float,
) -> tuple[list[dict], set[int], str]:
    """Return (sorted clean laps, excluded lap numbers, compound) for a stint.

    Shared logic between summarise_stints and summarise_stints_with_sectors.
    """
    lap_start = stint.get("lap_start")
    lap_end = stint.get("lap_end")
    if lap_start is None or lap_end is None:
        return [], set(), "UNKNOWN"

    stint_laps = sorted(
        (
            lap for lap in laps
            if (
                lap.get("lap_number") is not None
                and lap_start <= lap["lap_number"] <= lap_end
                and lap.get("lap_duration") is not None
                and not lap.get("is_pit_out_lap")
            )
        ),
        key=lambda l: l["lap_number"],
    )

    if not stint_laps:
        return [], set(), "UNKNOWN"

    compound = (stint.get("compound") or "UNKNOWN").upper()

    excluded: set[int] = set()
    if len(stint_laps) > 2:
        # Use interior laps for the reference mean so edge outliers
        # don't inflate the threshold used to detect them.
        interior = stint_laps[1:-1]
        ref_mean = statistics.mean(lap["lap_duration"] for lap in interior)
        upper = ref_mean * (1 + threshold)

        if stint_laps[0]["lap_duration"] > upper:
            excluded.add(stint_laps[0]["lap_number"])
        if stint_laps[-1]["lap_duration"] > upper:
            excluded.add(stint_laps[-1]["lap_number"])
    # 2-lap stints: no interior reference — keep both laps

    clean_laps = [lap for lap in stint_laps if lap["lap_number"] not in excluded]
    return clean_laps, excluded, compound


def summarise_stints(
    laps: list[dict],
    stints: list[dict],
    threshold: float = 0.07,
) -> list[dict]:
    """Summarise all stints, trimming only edge-lap (first/last) outliers.

    For each stint the first and last laps are checked against the stint mean.
    If either exceeds the mean by more than *threshold* (default 7 %) it is
    excluded from the statistics (and later from charts).  Mid-stint laps are
    never removed regardless of deviation.
    """
    summaries: list[dict] = []
    for stint in stints:
        clean_laps, excluded, compound = _compute_stint_clean_laps(
            laps, stint, threshold,
        )
        if not clean_laps:
            continue

        clean_durations = [l["lap_duration"] for l in clean_laps]

        summaries.append({
            "stint_number": stint.get("stint_number", "?"),
            "compound": compound,
            "lap_start": stint.get("lap_start"),
            "lap_end": stint.get("lap_end"),
            "num_laps": len(clean_durations),
            "excluded_laps": excluded,
            "avg_time": statistics.mean(clean_durations),
            "best_time": min(clean_durations),
            "std_dev": (
                statistics.stdev(clean_durations)
                if len(clean_durations) > 1
                else 0.0
            ),
        })

    return summaries


def summarise_stints_with_sectors(
    laps: list[dict],
    stints: list[dict],
    threshold: float = 0.07,
) -> list[dict]:
    """Like summarise_stints but also computes avg_sector_1/2/3.

    Sector averages are computed from the same clean (non-excluded) laps.
    Laps missing sector data are excluded from sector averages only (not
    from overall lap time stats).
    """
    summaries: list[dict] = []
    for stint in stints:
        clean_laps, excluded, compound = _compute_stint_clean_laps(
            laps, stint, threshold,
        )
        if not clean_laps:
            continue

        clean_durations = [l["lap_duration"] for l in clean_laps]

        sector_avgs: dict[str, float | None] = {}
        sector_bests: dict[str, float | None] = {}
        for sector_key in ("duration_sector_1", "duration_sector_2", "duration_sector_3"):
            sector_vals = [
                lap[sector_key] for lap in clean_laps
                if lap.get(sector_key) is not None
            ]
            sector_avgs[sector_key] = (
                statistics.mean(sector_vals) if sector_vals else None
            )
            sector_bests[sector_key] = (
                min(sector_vals) if sector_vals else None
            )

        summaries.append({
            "stint_number": stint.get("stint_number", "?"),
            "compound": compound,
            "lap_start": stint.get("lap_start"),
            "lap_end": stint.get("lap_end"),
            "num_laps": len(clean_durations),
            "excluded_laps": excluded,
            "avg_time": statistics.mean(clean_durations),
            "best_time": min(clean_durations),
            "std_dev": (
                statistics.stdev(clean_durations)
                if len(clean_durations) > 1
                else 0.0
            ),
            "avg_sector_1": sector_avgs["duration_sector_1"],
            "avg_sector_2": sector_avgs["duration_sector_2"],
            "avg_sector_3": sector_avgs["duration_sector_3"],
            "best_sector_1": sector_bests["duration_sector_1"],
            "best_sector_2": sector_bests["duration_sector_2"],
            "best_sector_3": sector_bests["duration_sector_3"],
        })

    return summaries
