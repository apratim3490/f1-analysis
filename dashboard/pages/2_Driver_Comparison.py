"""F1 Driver Comparison — compare up to 4 drivers side-by-side."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from shared import (
    PLOTLY_LAYOUT_DEFAULTS,
    DriverComparisonService,
    F1DataError,
    assign_driver_colors,
    format_lap_time,
    get_repository,
    render_session_sidebar,
)

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="F1 Driver Comparison",
    page_icon="\U0001f3ce\ufe0f",
    layout="wide",
)

# ── Sidebar ──────────────────────────────────────────────────────────────────

st.sidebar.title("Driver Comparison")

selection = render_session_sidebar()
if selection is None:
    st.stop()

session_key = selection.session_key
meeting_name = selection.meeting_name
session_name = selection.session_name
is_practice = selection.is_practice
drivers = selection.drivers

# Build driver label map
driver_map: dict[str, dict] = {
    f"{d.get('name_acronym', '???')} — {d.get('full_name', 'Unknown')}": d
    for d in drivers
    if d.get("driver_number")
}

if not driver_map:
    st.sidebar.warning("No valid drivers found for this session.")
    st.stop()

selected_labels = st.sidebar.multiselect(
    "Compare Drivers",
    list(driver_map.keys()),
    max_selections=4,
)

if len(selected_labels) < 2:
    st.info("Select 2\u20134 drivers from the sidebar to compare.")
    st.stop()

selected_drivers = [driver_map[label] for label in selected_labels]


# ── Color assignment ─────────────────────────────────────────────────────────

driver_colors = assign_driver_colors(selected_drivers)


# ── Service setup & data fetch ───────────────────────────────────────────────

repo = get_repository()
service = DriverComparisonService(repo)

with st.spinner("Loading driver data..."):
    try:
        driver_data, all_laps, weather = service.fetch_comparison_data(
            session_key,
            [d["driver_number"] for d in selected_drivers],
        )
    except F1DataError as exc:
        st.error(f"Failed to load driver data: {exc}")
        st.stop()


# ── A. Header ────────────────────────────────────────────────────────────────

st.markdown(f"## Driver Comparison — {meeting_name}, {session_name}")

header_cols = st.columns(len(selected_drivers))
for i, d in enumerate(selected_drivers):
    dn = d["driver_number"]
    color = driver_colors[dn]
    with header_cols[i]:
        if d.get("headshot_url"):
            st.image(d["headshot_url"], width=100)
        st.markdown(
            f"**{d.get('full_name', 'Unknown')}**  \n"
            f"{d.get('team_name', '')} | #{dn}"
        )
        st.markdown(
            f'<div style="height:4px;background:{color};border-radius:2px;'
            f'margin-bottom:0.5rem"></div>',
            unsafe_allow_html=True,
        )


# ── B. Best Lap Time + Ideal Lap ─────────────────────────────────────────────

st.subheader("Best Lap Time")

best_laps = service.compute_best_laps(driver_data, all_laps, selected_drivers)
metric_cols = st.columns(len(selected_drivers))
for i, bl in enumerate(best_laps):
    with metric_cols[i]:
        st.metric(bl.acronym, format_lap_time(bl.best_lap), delta=bl.delta)
        if bl.ideal_lap is not None:
            st.caption(f"Ideal: {format_lap_time(bl.ideal_lap)}")


# ── C. Stint Comparison ─────────────────────────────────────────────────────

if is_practice:
    st.subheader("Stint Comparison (Top 3, >5 laps, std dev < 2s)")
else:
    st.subheader("Stint Comparison (All stints, >5 laps)")

stint_table_rows, stint_raw, stint_insights = service.compute_stint_comparison(
    driver_data, selected_drivers, driver_colors, is_practice,
    weather=weather,
)

if not stint_table_rows:
    if is_practice:
        st.info("No consistent stint data available (all stints have <6 laps or std dev >= 2s).")
    else:
        st.info("No stint data available (all stints have <6 laps).")
else:
    col_config = {
        "Driver": st.column_config.TextColumn("Driver", help="Driver acronym"),
        "Compound": st.column_config.TextColumn("Compound", help="Tyre compound used in the stint"),
        "Avg Time": st.column_config.TextColumn("Avg Time", help="Mean lap time across clean laps (edge outliers excluded)"),
        "Best Time": st.column_config.TextColumn("Best Time", help="Fastest single lap in the stint"),
        "Ideal": st.column_config.TextColumn("Ideal", help="Theoretical best: best S1 + best S2 + best S3 within the stint"),
        "Laps": st.column_config.NumberColumn("Laps", help="Number of clean laps (after edge-lap outlier removal)"),
        "Avg S1": st.column_config.TextColumn("Avg S1", help="Average sector 1 time across clean laps"),
        "Avg S2": st.column_config.TextColumn("Avg S2", help="Average sector 2 time across clean laps"),
        "Avg S3": st.column_config.TextColumn("Avg S3", help="Average sector 3 time across clean laps"),
        "Best S1": st.column_config.TextColumn("Best S1", help="Fastest sector 1 in the stint"),
        "Best S2": st.column_config.TextColumn("Best S2", help="Fastest sector 2 in the stint"),
        "Best S3": st.column_config.TextColumn("Best S3", help="Fastest sector 3 in the stint"),
        "Std Dev": st.column_config.TextColumn("Std Dev", help="Standard deviation of lap times — lower means more consistent pace"),
    }
    if stint_table_rows and "Track Temp" in stint_table_rows[0]:
        col_config["Track Temp"] = st.column_config.TextColumn(
            "Track Temp", help="Estimated track temperature during the stint",
        )

    st.dataframe(
        stint_table_rows,
        use_container_width=True,
        hide_index=True,
        column_config=col_config,
    )

    if stint_insights is not None:
        insights: list[str] = []
        insights.append(
            f"**Fastest avg pace:** {stint_insights.fastest_avg[0]} "
            f"({format_lap_time(stint_insights.fastest_avg[1])} on {stint_insights.fastest_avg[2]})"
        )
        insights.append(
            f"**Most consistent:** {stint_insights.most_consistent[0]} "
            f"({stint_insights.most_consistent[1]:.3f}s std dev on {stint_insights.most_consistent[2]})"
        )
        if stint_insights.best_ideal is not None:
            insights.append(
                f"**Best ideal lap:** {stint_insights.best_ideal[0]} "
                f"({format_lap_time(stint_insights.best_ideal[1])} on {stint_insights.best_ideal[2]})"
            )
        for sector_num, (driver, time_val) in stint_insights.best_sectors.items():
            insights.append(
                f"**Best {sector_num}:** {driver} ({format_lap_time(time_val)})"
            )

        st.caption("Key Insights")
        st.markdown("  \n".join(insights))


# ── D. Speed Trap Comparison ────────────────────────────────────────────────

st.subheader("Speed Trap Comparison")

with st.expander("What are I1, I2, and ST?"):
    st.markdown(
        "**I1 (Intermediate 1)** — Speed measured at the **sector 1 boundary**. "
        "This is where the timing loop splits sector 1 from sector 2.  \n"
        "**I2 (Intermediate 2)** — Speed measured at the **sector 2 boundary**. "
        "This is where the timing loop splits sector 2 from sector 3.  \n"
        "**ST (Speed Trap)** — Speed measured by a dedicated sensor on the "
        "**longest straight**, typically where cars reach peak velocity.  \n\n"
        "Exact positions vary by circuit and are set by the FIA Race Director "
        "for each event. I1 and I2 always correspond to sector split points, "
        "while ST is placed independently on the fastest part of the track."
    )

speed_entries, session_max_speeds, session_speed_holder = service.compute_speed_traps(
    driver_data, all_laps, drivers, selected_drivers, driver_colors,
)

has_any_speed = any(
    any(s > 0 for s in entry["max_speeds"]) for entry in speed_entries
)

fig_speed = go.Figure()

for entry in speed_entries:
    fig_speed.add_trace(go.Bar(
        x=entry["zone_labels"],
        y=entry["max_speeds"],
        name=entry["acronym"],
        marker_color=entry["color"],
        hovertemplate="%{y:.1f} km/h<extra></extra>",
    ))

if session_max_speeds:
    speed_zones = ["I1", "I2", "ST"]
    ref_values = [session_max_speeds.get(label, 0) for label in speed_zones]
    ref_hover = [
        f"{v:.1f} km/h — {session_speed_holder.get(label, '?')}<extra></extra>"
        for label, v in zip(speed_zones, ref_values)
    ]
    fig_speed.add_trace(go.Bar(
        x=speed_zones,
        y=ref_values,
        name="Session Best",
        marker_color="#44DD44",
        hovertemplate=ref_hover,
        text=[session_speed_holder.get(label, "") for label in speed_zones],
        textposition="outside",
        textfont=dict(color="#44DD44", size=10),
    ))

if not has_any_speed:
    st.info("No speed trap data available.")
else:
    all_speed_vals = [v for trace in fig_speed.data for v in trace.y if v > 0]
    if all_speed_vals:
        s_min = min(all_speed_vals)
        s_max = max(all_speed_vals)
        s_pad = (s_max - s_min) * 0.15 if s_max > s_min else 10
        speed_range: list[float] | None = [max(0, s_min - s_pad), s_max + s_pad]
    else:
        speed_range = None

    fig_speed.update_layout(
        **PLOTLY_LAYOUT_DEFAULTS,
        barmode="group",
        yaxis_title="Max Speed (km/h)",
        yaxis_range=speed_range,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=400,
    )
    st.plotly_chart(fig_speed, use_container_width=True)


# ── E. Sector Time Comparison (Fastest Lap) ─────────────────────────────────

st.subheader("Sector Time Comparison (Fastest Lap)")

sector_entries = service.compute_sector_comparison(
    driver_data, selected_drivers, driver_colors,
)

if not sector_entries:
    st.info("No sector time data available.")
else:
    acronyms = [se.acronym for se in sector_entries]

    fig_sectors = go.Figure()

    fig_sectors.add_trace(go.Bar(
        x=acronyms,
        y=[se.s1 for se in sector_entries],
        name="S1", marker_color="#FF3333",
        hovertemplate="S1: %{y:.3f}s<extra></extra>",
    ))
    fig_sectors.add_trace(go.Bar(
        x=acronyms,
        y=[se.s2 for se in sector_entries],
        name="S2", marker_color="#FFC700",
        hovertemplate="S2: %{y:.3f}s<extra></extra>",
    ))
    fig_sectors.add_trace(go.Bar(
        x=acronyms,
        y=[se.s3 for se in sector_entries],
        name="S3", marker_color="#9933FF",
        hovertemplate="S3: %{y:.3f}s<extra></extra>",
    ))

    for se in sector_entries:
        fig_sectors.add_annotation(
            x=se.acronym,
            y=se.total,
            text=format_lap_time(se.total),
            showarrow=False,
            yshift=10,
            font=dict(color="#F0F0F0", size=12),
        )

    fig_sectors.update_layout(
        **PLOTLY_LAYOUT_DEFAULTS,
        barmode="stack",
        yaxis_title="Time (s)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=400,
    )
    st.plotly_chart(fig_sectors, use_container_width=True)


# ── F. Telemetry (Best Lap) ────────────────────────────────────────────────

with st.spinner("Loading telemetry data..."):
    try:
        telemetry_data = service.fetch_telemetry_for_best_laps(
            session_key, driver_data, selected_drivers, driver_colors,
        )
    except F1DataError:
        telemetry_data = {}

if telemetry_data:
    # ── F1. Track Map Animation ─────────────────────────────────────────

    track_map = DriverComparisonService.compute_track_map(telemetry_data)

    st.subheader("Track Map (Best Lap)")

    if track_map is None:
        st.info("Track map data unavailable for the selected drivers.")
    else:
        # Base track outline
        fig_track = go.Figure()
        fig_track.add_trace(go.Scatter(
            x=list(track_map.track_x),
            y=list(track_map.track_y),
            mode="lines",
            line=dict(color="#555555", width=2),
            name="Track",
            hoverinfo="skip",
        ))

        # Initial driver positions (first frame)
        if track_map.frames:
            first_frame = track_map.frames[0]
            for dp in first_frame.driver_positions:
                fig_track.add_trace(go.Scatter(
                    x=[dp.x],
                    y=[dp.y],
                    mode="markers+text",
                    marker=dict(size=12, color=track_map.driver_colors.get(dp.acronym, "#FFFFFF")),
                    text=[dp.acronym],
                    textposition="top center",
                    textfont=dict(size=10, color=track_map.driver_colors.get(dp.acronym, "#FFFFFF")),
                    name=dp.acronym,
                    showlegend=True,
                ))

        # Animation frames
        plotly_frames: list[go.Frame] = []
        for frame in track_map.frames:
            frame_data: list[go.Scatter] = [
                go.Scatter(
                    x=list(track_map.track_x),
                    y=list(track_map.track_y),
                    mode="lines",
                    line=dict(color="#555555", width=2),
                ),
            ]
            for dp in frame.driver_positions:
                frame_data.append(go.Scatter(
                    x=[dp.x],
                    y=[dp.y],
                    mode="markers+text",
                    marker=dict(size=12, color=track_map.driver_colors.get(dp.acronym, "#FFFFFF")),
                    text=[dp.acronym],
                    textposition="top center",
                    textfont=dict(size=10, color=track_map.driver_colors.get(dp.acronym, "#FFFFFF")),
                ))
            plotly_frames.append(go.Frame(data=frame_data, name=f"{frame.t:.1f}s"))

        fig_track.frames = plotly_frames

        fig_track.update_layout(
            **PLOTLY_LAYOUT_DEFAULTS,
            height=600,
            xaxis=dict(scaleanchor="y", visible=False),
            yaxis=dict(visible=False),
            updatemenus=[dict(
                type="buttons",
                showactive=False,
                y=0,
                x=0.5,
                xanchor="center",
                buttons=[
                    dict(label="Play", method="animate", args=[
                        None,
                        dict(frame=dict(duration=track_map.frame_interval_ms, redraw=True), fromcurrent=True),
                    ]),
                    dict(label="Pause", method="animate", args=[
                        [None],
                        dict(frame=dict(duration=0, redraw=False), mode="immediate"),
                    ]),
                ],
            )],
        )
        st.plotly_chart(fig_track, use_container_width=True)

    # ── F2. Speed vs Time ───────────────────────────────────────────────

    speed_traces = DriverComparisonService.compute_speed_trace(telemetry_data)

    st.subheader("Speed vs Time (Best Lap)")

    if not speed_traces:
        st.info("Speed telemetry unavailable for the selected drivers.")
    else:
        fig_speed_telem = go.Figure()
        for trace in speed_traces:
            fig_speed_telem.add_trace(go.Scatter(
                x=[p.t for p in trace.points],
                y=[p.value for p in trace.points],
                mode="lines",
                name=trace.acronym,
                line=dict(color=trace.color, width=2),
                hovertemplate="%{y:.0f} km/h at %{x:.1f}s<extra></extra>",
            ))

        fig_speed_telem.update_layout(
            **PLOTLY_LAYOUT_DEFAULTS,
            height=400,
            xaxis_title="Time into Lap (s)",
            yaxis_title="Speed (km/h)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_speed_telem, use_container_width=True)

    # ── F3. RPM vs Time ────────────────────────────────────────────────

    rpm_traces = DriverComparisonService.compute_rpm_trace(telemetry_data)

    st.subheader("RPM vs Time (Best Lap)")

    if not rpm_traces:
        st.info("RPM telemetry unavailable for the selected drivers.")
    else:
        fig_rpm = go.Figure()
        for trace in rpm_traces:
            fig_rpm.add_trace(go.Scatter(
                x=[p.t for p in trace.points],
                y=[p.value for p in trace.points],
                mode="lines",
                name=trace.acronym,
                line=dict(color=trace.color, width=2),
                hovertemplate="%{y:.0f} RPM at %{x:.1f}s<extra></extra>",
            ))

        fig_rpm.update_layout(
            **PLOTLY_LAYOUT_DEFAULTS,
            height=400,
            xaxis_title="Time into Lap (s)",
            yaxis_title="RPM",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_rpm, use_container_width=True)

else:
    st.subheader("Telemetry (Best Lap)")
    st.info("Telemetry data unavailable for the selected drivers. This feature requires the OpenF1 backend.")
