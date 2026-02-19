"""F1 Driver Performance Dashboard — Streamlit + Plotly + OpenF1 API."""

from __future__ import annotations

import statistics

import plotly.graph_objects as go
import streamlit as st

from openf1.exceptions import OpenF1Error

from shared import (
    COMPOUND_COLORS,
    F1_RED,
    PLOTLY_LAYOUT_DEFAULTS,
    fetch_all_laps,
    fetch_laps,
    fetch_pits,
    fetch_stints,
    format_delta,
    format_lap_time,
    get_compound_for_lap,
    render_session_sidebar,
    summarise_stints,
)

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="F1 Driver Performance",
    page_icon="\U0001f3ce\ufe0f",
    layout="wide",
)


# ── Sidebar — cascading selection ────────────────────────────────────────────

st.sidebar.title("F1 Performance Dashboard")

selection = render_session_sidebar()
if selection is None:
    st.stop()

selected_session_key = selection.session_key
selected_meeting_name = selection.meeting_name
selected_session_name = selection.session_name
is_practice = selection.is_practice
drivers = selection.drivers

# Driver selector (single-driver page only)
driver_options = {
    f"{d.get('name_acronym', '???')} — {d.get('full_name', 'Unknown')}": d
    for d in drivers
    if d.get("driver_number")
}
if not driver_options:
    st.sidebar.warning("No valid drivers found for this session.")
    st.stop()
selected_driver_label = st.sidebar.selectbox("Driver", list(driver_options.keys()))
driver = driver_options[selected_driver_label]
driver_number = driver["driver_number"]
team_color = f"#{driver['team_colour']}" if driver.get("team_colour") else F1_RED


# ── Fetch driver data ───────────────────────────────────────────────────────

with st.spinner("Loading lap data..."):
    try:
        laps = fetch_laps(selected_session_key, driver_number)
        all_laps = fetch_all_laps(selected_session_key)
        stints = fetch_stints(selected_session_key, driver_number)
        pits = fetch_pits(selected_session_key, driver_number)
    except OpenF1Error as exc:
        st.error(f"Failed to load driver data: {exc}")
        st.stop()


# ── Header ───────────────────────────────────────────────────────────────────

header_cols = st.columns([1, 4])

with header_cols[0]:
    if driver.get("headshot_url"):
        st.image(driver["headshot_url"], width=120)

with header_cols[1]:
    st.markdown(
        f"# {driver.get('full_name', 'Unknown Driver')}"
        f"  \n**{driver.get('team_name', '')}** | #{driver_number}"
        f"  \n{selected_meeting_name} — {selected_session_name}"
    )

# Team color accent bar
st.markdown(
    f'<div style="height:4px;background:{team_color};border-radius:2px;'
    f'margin-bottom:1rem"></div>',
    unsafe_allow_html=True,
)


# ── KPI metrics ──────────────────────────────────────────────────────────────

valid_laps = [lap for lap in laps if lap.get("lap_duration") is not None]
all_valid_laps = [lap for lap in all_laps if lap.get("lap_duration") is not None]

total_laps = len(laps)
best_lap = min((lap["lap_duration"] for lap in valid_laps), default=None)
session_best = min(
    (lap["lap_duration"] for lap in all_valid_laps),
    default=None,
)

if is_practice:
    kpi1, kpi2 = st.columns(2)
    kpi1.metric("Total Laps", total_laps)
    kpi2.metric(
        "Best Lap", format_lap_time(best_lap),
        delta=format_delta(best_lap, session_best),
    )
else:
    avg_lap = (
        statistics.mean(
            lap["lap_duration"]
            for lap in valid_laps
            if not lap.get("is_pit_out_lap")
        )
        if any(not lap.get("is_pit_out_lap") for lap in valid_laps)
        else None
    )
    pit_count = len(pits)

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Total Laps", total_laps)
    kpi2.metric(
        "Best Lap", format_lap_time(best_lap),
        delta=format_delta(best_lap, session_best),
    )
    kpi3.metric("Avg Lap", format_lap_time(avg_lap))
    kpi4.metric("Pit Stops", pit_count)


# ── Pre-compute stint summaries (practice mode) ────────────────────────────

stint_summaries: list[dict] = []
_edge_excluded_laps: set[int] = set()
if is_practice:
    _all_stint_summaries = summarise_stints(laps, stints)
    stint_summaries = [s for s in _all_stint_summaries if s["num_laps"] > 5]
    for _s in stint_summaries:
        _edge_excluded_laps.update(_s["excluded_laps"])

# ── Chart 1: Lap Time Progression ───────────────────────────────────────────

st.subheader("Lap Time Progression")

if not valid_laps:
    st.warning("No lap time data available.")
else:
    clean_laps = [
        lap for lap in valid_laps
        if not lap.get("is_pit_out_lap")
    ]
    pit_out_laps = [
        lap for lap in valid_laps
        if lap.get("is_pit_out_lap")
    ]

    session_durations = [
        lap["lap_duration"] for lap in all_valid_laps
        if not lap.get("is_pit_out_lap")
    ]
    session_median = statistics.median(session_durations) if session_durations else None

    fig_progression = go.Figure()

    if is_practice and clean_laps:
        # Group laps by compound for color-coded traces, excluding edge outliers
        compound_laps: dict[str, list[dict]] = {}
        for lap in clean_laps:
            if lap["lap_number"] in _edge_excluded_laps:
                continue
            compound = get_compound_for_lap(lap["lap_number"], stints)
            compound_laps.setdefault(compound, []).append(lap)

        for compound, c_laps in compound_laps.items():
            color = COMPOUND_COLORS.get(compound, COMPOUND_COLORS["UNKNOWN"])
            fig_progression.add_trace(go.Scatter(
                x=[lap["lap_number"] for lap in c_laps],
                y=[lap["lap_duration"] for lap in c_laps],
                mode="markers+lines",
                name=compound,
                line=dict(color=color, width=2),
                marker=dict(size=6, color=color),
                connectgaps=False,
                hovertemplate=(
                    "Lap %{x}<br>%{text}<br>" + compound + "<extra></extra>"
                ),
                text=[format_lap_time(lap["lap_duration"]) for lap in c_laps],
            ))
    elif clean_laps:
        # Standard single-color line for non-practice sessions
        fig_progression.add_trace(go.Scatter(
            x=[lap["lap_number"] for lap in clean_laps],
            y=[lap["lap_duration"] for lap in clean_laps],
            mode="lines+markers",
            name="Lap Time",
            line=dict(color=team_color, width=2),
            marker=dict(size=5),
            hovertemplate="Lap %{x}<br>%{text}<extra></extra>",
            text=[format_lap_time(lap["lap_duration"]) for lap in clean_laps],
        ))

    # Pit out laps as distinct markers
    if pit_out_laps:
        fig_progression.add_trace(go.Scatter(
            x=[lap["lap_number"] for lap in pit_out_laps],
            y=[lap["lap_duration"] for lap in pit_out_laps],
            mode="markers",
            name="Pit Out Lap",
            marker=dict(
                size=10, color="rgba(0,0,0,0)",
                line=dict(color="#888888", width=2),
                symbol="diamond-open",
            ),
            hovertemplate="Lap %{x} (pit out)<br>%{text}<extra></extra>",
            text=[format_lap_time(lap["lap_duration"]) for lap in pit_out_laps],
        ))

    # Session median reference line
    if session_median is not None:
        fig_progression.add_hline(
            y=session_median,
            line_dash="dash", line_color="#888888", line_width=1,
            annotation_text=f"Session median: {format_lap_time(session_median)}",
            annotation_position="top right",
            annotation_font_color="#888888",
        )

    # Session best reference line
    if session_best is not None:
        fig_progression.add_hline(
            y=session_best,
            line_dash="dot", line_color="#44DD44", line_width=1,
            annotation_text=f"Session best: {format_lap_time(session_best)}",
            annotation_position="bottom right",
            annotation_font_color="#44DD44",
        )

    # Tight y-axis scaling around plotted lap times
    plotted_laps = (
        [l for l in clean_laps if l["lap_number"] not in _edge_excluded_laps]
        if is_practice
        else clean_laps
    )
    all_chart_durations = [lap["lap_duration"] for lap in plotted_laps]
    if pit_out_laps:
        all_chart_durations += [lap["lap_duration"] for lap in pit_out_laps]
    if all_chart_durations:
        y_min = min(all_chart_durations)
        y_max = max(all_chart_durations)
        y_padding = (y_max - y_min) * 0.1 if y_max > y_min else 2.0
        y_range = [y_min - y_padding, y_max + y_padding]
    else:
        y_range = None

    fig_progression.update_layout(
        **PLOTLY_LAYOUT_DEFAULTS,
        xaxis_title="Lap Number",
        yaxis_title="Lap Time (s)",
        yaxis_range=y_range,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=400,
    )
    st.plotly_chart(fig_progression, use_container_width=True)


# ── Chart 2 & 3: Sector Breakdown + Speed Trap Comparison ───────────────────

col_sector, col_speed = st.columns(2)

# Sector Breakdown — stacked bar
with col_sector:
    st.subheader("Sector Breakdown")

    sector_laps = [
        lap for lap in laps
        if (
            lap.get("duration_sector_1") is not None
            and lap.get("duration_sector_2") is not None
            and lap.get("duration_sector_3") is not None
            and not lap.get("is_pit_out_lap")
        )
    ]

    if not sector_laps:
        st.warning("No sector time data available.")
    else:
        lap_numbers = [lap["lap_number"] for lap in sector_laps]

        fig_sectors = go.Figure()

        if is_practice:
            # Color bars by compound — each bar outlined with compound color
            compounds = [
                get_compound_for_lap(lap["lap_number"], stints) for lap in sector_laps
            ]
            bar_colors = [
                COMPOUND_COLORS.get(c, COMPOUND_COLORS["UNKNOWN"]) for c in compounds
            ]

            fig_sectors.add_trace(go.Bar(
                x=lap_numbers,
                y=[lap["duration_sector_1"] for lap in sector_laps],
                name="S1",
                marker_color="#FF3333",
                hovertemplate=[
                    f"S1: {lap['duration_sector_1']:.3f}s | {c}<extra></extra>"
                    for lap, c in zip(sector_laps, compounds, strict=True)
                ],
            ))
            fig_sectors.add_trace(go.Bar(
                x=lap_numbers,
                y=[lap["duration_sector_2"] for lap in sector_laps],
                name="S2",
                marker_color="#FFC700",
                hovertemplate=[
                    f"S2: {lap['duration_sector_2']:.3f}s | {c}<extra></extra>"
                    for lap, c in zip(sector_laps, compounds, strict=True)
                ],
            ))
            fig_sectors.add_trace(go.Bar(
                x=lap_numbers,
                y=[lap["duration_sector_3"] for lap in sector_laps],
                name="S3",
                marker_color="#9933FF",
                hovertemplate=[
                    f"S3: {lap['duration_sector_3']:.3f}s | {c}<extra></extra>"
                    for lap, c in zip(sector_laps, compounds, strict=True)
                ],
            ))

            # Add compound color markers along the x-axis
            fig_sectors.add_trace(go.Scatter(
                x=lap_numbers,
                y=[0] * len(lap_numbers),
                mode="markers",
                name="Compound",
                marker=dict(
                    size=8,
                    color=bar_colors,
                    symbol="square",
                ),
                showlegend=False,
                hovertemplate=[
                    f"Lap {ln}: {c}<extra></extra>"
                    for ln, c in zip(lap_numbers, compounds, strict=True)
                ],
            ))
        else:
            fig_sectors.add_trace(go.Bar(
                x=lap_numbers,
                y=[lap["duration_sector_1"] for lap in sector_laps],
                name="S1",
                marker_color="#FF3333",
                hovertemplate="S1: %{y:.3f}s<extra></extra>",
            ))
            fig_sectors.add_trace(go.Bar(
                x=lap_numbers,
                y=[lap["duration_sector_2"] for lap in sector_laps],
                name="S2",
                marker_color="#FFC700",
                hovertemplate="S2: %{y:.3f}s<extra></extra>",
            ))
            fig_sectors.add_trace(go.Bar(
                x=lap_numbers,
                y=[lap["duration_sector_3"] for lap in sector_laps],
                name="S3",
                marker_color="#9933FF",
                hovertemplate="S3: %{y:.3f}s<extra></extra>",
            ))

        fig_sectors.update_layout(
            **PLOTLY_LAYOUT_DEFAULTS,
            barmode="stack",
            xaxis_title="Lap Number",
            yaxis_title="Time (s)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=400,
        )
        st.plotly_chart(fig_sectors, use_container_width=True)

# Speed Trap Comparison — grouped bar
with col_speed:
    st.subheader("Speed Trap Comparison")

    speed_fields = [
        ("i1_speed", "I1 Speed"),
        ("i2_speed", "I2 Speed"),
        ("st_speed", "Speed Trap"),
    ]

    driver_speeds: dict[str, list[float]] = {}
    session_speeds: dict[str, list[float]] = {}

    for field, _ in speed_fields:
        driver_speeds[field] = [
            lap[field] for lap in laps
            if lap.get(field) is not None
        ]
        session_speeds[field] = [
            lap[field] for lap in all_laps
            if lap.get(field) is not None
        ]

    has_speed_data = any(len(v) > 0 for v in driver_speeds.values())

    if not has_speed_data:
        st.warning("No speed trap data available.")
    else:
        active_fields = [
            (field, label) for field, label in speed_fields
            if driver_speeds[field]
        ]
        categories = [label for _, label in active_fields]
        driver_avgs = [statistics.mean(driver_speeds[f]) for f, _ in active_fields]
        driver_maxes = [max(driver_speeds[f]) for f, _ in active_fields]
        session_bests = [
            max(session_speeds[f]) if session_speeds[f] else 0
            for f, _ in active_fields
        ]

        fig_speed = go.Figure()
        fig_speed.add_trace(go.Bar(
            x=categories, y=driver_avgs,
            name="Driver Avg", marker_color=team_color,
            hovertemplate="%{y:.1f} km/h<extra></extra>",
        ))
        fig_speed.add_trace(go.Bar(
            x=categories, y=driver_maxes,
            name="Driver Max", marker_color="#BBBBBB",
            hovertemplate="%{y:.1f} km/h<extra></extra>",
        ))
        fig_speed.add_trace(go.Bar(
            x=categories, y=session_bests,
            name="Session Best", marker_color="#44DD44",
            hovertemplate="%{y:.1f} km/h<extra></extra>",
        ))

        # Tight y-axis: start near the lowest value
        all_speed_vals = driver_avgs + driver_maxes + session_bests
        speed_min = min(all_speed_vals) if all_speed_vals else 0
        speed_max = max(all_speed_vals) if all_speed_vals else 0
        speed_pad = (speed_max - speed_min) * 0.15 if speed_max > speed_min else 10
        speed_y_range = [
            max(0, speed_min - speed_pad),
            speed_max + speed_pad,
        ]

        fig_speed.update_layout(
            **PLOTLY_LAYOUT_DEFAULTS,
            barmode="group",
            yaxis_title="Speed (km/h)",
            yaxis_range=speed_y_range,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=400,
        )
        st.plotly_chart(fig_speed, use_container_width=True)


# ── Practice: Stint Summary & Chart ─────────────────────────────────────────

if is_practice:
    st.subheader("Stint Summary (>5 laps, excl. warm-up/cool-down)")

    if not stint_summaries:
        st.info("No stints with more than 5 clean laps.")
    else:
        sim_rows = []
        for sim in stint_summaries:
            excluded_note = (
                f" ({len(sim['excluded_laps'])} edge lap(s) excluded)"
                if sim["excluded_laps"]
                else ""
            )
            sim_rows.append({
                "Stint #": sim["stint_number"],
                "Compound": sim["compound"],
                "Laps": f"{sim['lap_start']}\u2013{sim['lap_end']}",
                "# Laps": f"{sim['num_laps']}{excluded_note}",
                "Avg Time": format_lap_time(sim["avg_time"]),
                "Best Time": format_lap_time(sim["best_time"]),
                "Std Dev": f"{sim['std_dev']:.3f}s",
            })

        st.table(sim_rows)

        # Chart: lap times per stint (edge outliers excluded)
        # Only plot stints with >=2 valid laps (enough to draw a line)
        chart_stints = [s for s in stint_summaries if s["num_laps"] >= 2]

        if chart_stints:
            fig_sims = go.Figure()
            all_sim_durations: list[float] = []

            for sim in chart_stints:
                compound = sim["compound"]
                color = COMPOUND_COLORS.get(compound, COMPOUND_COLORS["UNKNOWN"])
                label = f"Stint {sim['stint_number']} ({compound})"
                excluded = sim["excluded_laps"]

                stint_laps = sorted(
                    (
                        lap for lap in laps
                        if (
                            lap.get("lap_number") is not None
                            and sim["lap_start"] <= lap["lap_number"] <= sim["lap_end"]
                            and lap.get("lap_duration") is not None
                            and not lap.get("is_pit_out_lap")
                            and lap["lap_number"] not in excluded
                        )
                    ),
                    key=lambda l: l["lap_number"],
                )

                if not stint_laps:
                    continue

                durations = [lap["lap_duration"] for lap in stint_laps]
                all_sim_durations.extend(durations)

                fig_sims.add_trace(go.Scatter(
                    x=[lap["lap_number"] for lap in stint_laps],
                    y=durations,
                    mode="lines+markers",
                    name=label,
                    line=dict(color=color, width=2),
                    marker=dict(size=5, color=color),
                    hovertemplate=(
                        "Lap %{x}<br>%{text}<br>" + compound + "<extra></extra>"
                    ),
                    text=[format_lap_time(d) for d in durations],
                ))

                fig_sims.add_hline(
                    y=sim["avg_time"],
                    line_dash="dash", line_color=color, line_width=1,
                    annotation_text=(
                        f"Avg {label}: {format_lap_time(sim['avg_time'])}"
                    ),
                    annotation_font_color=color,
                    annotation_font_size=10,
                )

            # Tight y-axis for stint chart
            if all_sim_durations:
                sim_y_min = min(all_sim_durations)
                sim_y_max = max(all_sim_durations)
                sim_pad = (
                    (sim_y_max - sim_y_min) * 0.1
                    if sim_y_max > sim_y_min
                    else 2.0
                )
                sim_y_range = [sim_y_min - sim_pad, sim_y_max + sim_pad]
            else:
                sim_y_range = None

            fig_sims.update_layout(
                **PLOTLY_LAYOUT_DEFAULTS,
                xaxis_title="Lap Number",
                yaxis_title="Lap Time (s)",
                yaxis_range=sim_y_range,
                showlegend=True,
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1,
                ),
                height=400,
            )
            st.plotly_chart(fig_sims, use_container_width=True)


# ── Tire Strategy Timeline (non-practice only) ──────────────────────────────

if not is_practice:
    st.subheader("Tire Strategy")

    if not stints:
        st.warning("No stint data available.")
    else:
        fig_tires = go.Figure()

        for stint in stints:
            lap_start = stint.get("lap_start")
            lap_end = stint.get("lap_end")
            if lap_start is None or lap_end is None:
                continue
            compound = (stint.get("compound") or "UNKNOWN").upper()
            color = COMPOUND_COLORS.get(compound, COMPOUND_COLORS["UNKNOWN"])
            stint_num = stint.get("stint_number", "?")
            tyre_age = stint.get("tyre_age_at_start", 0) or 0

            fig_tires.add_trace(go.Bar(
                x=[lap_end - lap_start + 1],
                y=["Strategy"],
                base=[lap_start],
                orientation="h",
                name=f"Stint {stint_num}: {compound}",
                marker_color=color,
                marker_line=dict(color="#333333", width=1),
                text=f"{compound} ({lap_end - lap_start + 1} laps, age {tyre_age})",
                textposition="inside",
                textfont=dict(
                    color=(
                        "#000000"
                        if compound in ("MEDIUM", "HARD", "INTERMEDIATE")
                        else "#FFFFFF"
                    ),
                ),
                hovertemplate=(
                    f"Stint {stint_num}<br>"
                    f"{compound}<br>"
                    f"Laps {lap_start}\u2013{lap_end}<br>"
                    f"Tyre age at start: {tyre_age}"
                    "<extra></extra>"
                ),
            ))

        fig_tires.update_layout(
            **PLOTLY_LAYOUT_DEFAULTS,
            xaxis_title="Lap Number",
            showlegend=False,
            height=140,
            yaxis=dict(showticklabels=False),
            margin=dict(l=20, r=20, t=10, b=40),
        )
        st.plotly_chart(fig_tires, use_container_width=True)


# ── Pit Stop Table (non-practice only) ──────────────────────────────────────

if not is_practice:
    st.subheader("Pit Stops")

    if not pits:
        st.info("No pit stop data recorded for this driver.")
    else:
        pit_rows = []
        for i, pit in enumerate(pits, start=1):
            pit_rows.append({
                "Stop #": i,
                "Lap": pit.get("lap_number", "\u2014"),
                "Duration (s)": (
                    f"{pit['pit_duration']:.1f}"
                    if pit.get("pit_duration") is not None
                    else "\u2014"
                ),
            })

        st.table(pit_rows)
