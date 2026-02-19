"""F1 Driver Comparison — compare up to 4 drivers side-by-side."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from openf1.exceptions import OpenF1Error

from shared import (
    COMPARISON_COLORS,
    F1_RED,
    PLOTLY_LAYOUT_DEFAULTS,
    fetch_all_laps,
    fetch_laps,
    fetch_stints,
    format_delta,
    format_lap_time,
    render_session_sidebar,
    summarise_stints_with_sectors,
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


def assign_colors(driver_list: list[dict]) -> dict[int, str]:
    """Assign a unique color to each driver, handling teammate collisions."""
    colors: dict[int, str] = {}
    used_colors: set[str] = set()
    fallback_idx = 0

    for d in driver_list:
        raw = f"#{d['team_colour']}" if d.get("team_colour") else F1_RED
        color = raw.upper()

        if color in used_colors:
            # Teammate collision — pick a fallback
            found = False
            while fallback_idx < len(COMPARISON_COLORS):
                candidate = COMPARISON_COLORS[fallback_idx].upper()
                fallback_idx += 1
                if candidate not in used_colors:
                    color = candidate
                    found = True
                    break
            if not found:
                # All fallbacks exhausted — generate deterministic color
                dn = d.get("driver_number", 0)
                color = f"#{abs(hash(str(dn))) % 0xFFFFFF:06X}"

        used_colors.add(color)
        colors[d["driver_number"]] = color

    return colors


driver_colors = assign_colors(selected_drivers)


# ── Fetch data ───────────────────────────────────────────────────────────────

driver_data: dict[int, dict] = {}  # driver_number -> {laps, stints, ...}

with st.spinner("Loading driver data..."):
    try:
        all_laps = fetch_all_laps(session_key)
    except OpenF1Error as exc:
        st.error(f"Failed to load session laps: {exc}")
        st.stop()

    for d in selected_drivers:
        dn = d["driver_number"]
        try:
            d_laps = fetch_laps(session_key, dn)
            d_stints = fetch_stints(session_key, dn)
        except OpenF1Error as exc:
            st.error(f"Failed to load data for {d.get('name_acronym', dn)}: {exc}")
            st.stop()
        driver_data[dn] = {"laps": d_laps, "stints": d_stints}

# Session best lap
all_valid = [lap for lap in all_laps if lap.get("lap_duration") is not None]
session_best = min((lap["lap_duration"] for lap in all_valid), default=None)


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

metric_cols = st.columns(len(selected_drivers))
for i, d in enumerate(selected_drivers):
    dn = d["driver_number"]
    d_laps = driver_data[dn]["laps"]

    valid_laps = [
        lap for lap in d_laps
        if lap.get("lap_duration") is not None
    ]
    best = min((lap["lap_duration"] for lap in valid_laps), default=None)

    # Ideal lap: best S1 + best S2 + best S3 across all laps
    s1_vals = [lap["duration_sector_1"] for lap in d_laps if lap.get("duration_sector_1") is not None]
    s2_vals = [lap["duration_sector_2"] for lap in d_laps if lap.get("duration_sector_2") is not None]
    s3_vals = [lap["duration_sector_3"] for lap in d_laps if lap.get("duration_sector_3") is not None]
    ideal = (min(s1_vals) + min(s2_vals) + min(s3_vals)) if s1_vals and s2_vals and s3_vals else None

    with metric_cols[i]:
        st.metric(
            d.get("name_acronym", "???"),
            format_lap_time(best),
            delta=format_delta(best, session_best),
        )
        if ideal is not None:
            st.caption(f"Ideal: {format_lap_time(ideal)}")


# ── C. Stint Comparison ─────────────────────────────────────────────────────

if is_practice:
    st.subheader("Stint Comparison (Top 3, >5 laps, std dev < 2s)")
else:
    st.subheader("Stint Comparison (All stints, >5 laps)")

# Compute stint summaries per driver
stint_table_rows: list[dict] = []
# Raw numeric data per row for generating insights
stint_raw: list[dict] = []

for d in selected_drivers:
    dn = d["driver_number"]
    acronym = d.get("name_acronym", "???")
    color = driver_colors[dn]
    summaries = summarise_stints_with_sectors(
        driver_data[dn]["laps"],
        driver_data[dn]["stints"],
    )

    # Filter: >5 clean laps; in practice also require std_dev < 2s
    if is_practice:
        consistent = [
            s for s in summaries
            if s["num_laps"] > 5 and s["std_dev"] < 2.0
        ]
    else:
        consistent = [s for s in summaries if s["num_laps"] > 5]
    consistent.sort(key=lambda s: s["avg_time"])
    top3 = consistent if not is_practice else consistent[:3]

    for rank, s in enumerate(top3, start=1):
        best_s1 = s["best_sector_1"]
        best_s2 = s["best_sector_2"]
        best_s3 = s["best_sector_3"]
        ideal = (
            (best_s1 + best_s2 + best_s3)
            if best_s1 is not None and best_s2 is not None and best_s3 is not None
            else None
        )
        stint_table_rows.append({
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
        })
        stint_raw.append({
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

if not stint_table_rows:
    if is_practice:
        st.info("No consistent stint data available (all stints have <6 laps or std dev >= 2s).")
    else:
        st.info("No stint data available (all stints have <6 laps).")
else:
    st.dataframe(
        stint_table_rows,
        use_container_width=True,
        hide_index=True,
        column_config={
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
        },
    )

    # Key insights from stint data
    insights: list[str] = []

    # Fastest average pace
    fastest_avg = min(stint_raw, key=lambda r: r["avg_time"])
    insights.append(
        f"**Fastest avg pace:** {fastest_avg['driver']} "
        f"({format_lap_time(fastest_avg['avg_time'])} on {fastest_avg['compound']})"
    )

    # Most consistent stint
    most_consistent = min(stint_raw, key=lambda r: r["std_dev"])
    insights.append(
        f"**Most consistent:** {most_consistent['driver']} "
        f"({most_consistent['std_dev']:.3f}s std dev on {most_consistent['compound']})"
    )

    # Best ideal lap across stints
    ideals = [r for r in stint_raw if r["ideal"] is not None]
    if ideals:
        best_ideal = min(ideals, key=lambda r: r["ideal"])
        insights.append(
            f"**Best ideal lap:** {best_ideal['driver']} "
            f"({format_lap_time(best_ideal['ideal'])} on {best_ideal['compound']})"
        )

    # Best individual sectors across all stints
    for sector_num, key in [("S1", "best_s1"), ("S2", "best_s2"), ("S3", "best_s3")]:
        sector_rows = [r for r in stint_raw if r[key] is not None]
        if sector_rows:
            best = min(sector_rows, key=lambda r: r[key])
            insights.append(
                f"**Best {sector_num}:** {best['driver']} "
                f"({format_lap_time(best[key])})"
            )

    if insights:
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

speed_zones = [
    ("i1_speed", "I1"),
    ("i2_speed", "I2"),
    ("st_speed", "ST"),
]

has_any_speed = False
fig_speed = go.Figure()

# Session-best speeds across all drivers as reference
# Build driver_number -> driver info lookup from full driver list
driver_by_number: dict[int, dict] = {
    d["driver_number"]: d for d in drivers if d.get("driver_number")
}

session_max_speeds: dict[str, float] = {}
session_speed_holder: dict[str, str] = {}  # zone label -> "ACR (Team)"
for field, label in speed_zones:
    zone_laps = [lap for lap in all_laps if lap.get(field) is not None]
    if zone_laps:
        best_lap = max(zone_laps, key=lambda lap: lap[field])
        session_max_speeds[label] = best_lap[field]
        holder = driver_by_number.get(best_lap.get("driver_number", 0), {})
        holder_name = holder.get("name_acronym", "???")
        holder_team = holder.get("team_name", "")
        session_speed_holder[label] = f"{holder_name} ({holder_team})" if holder_team else holder_name

for d in selected_drivers:
    dn = d["driver_number"]
    acronym = d.get("name_acronym", "???")
    color = driver_colors[dn]
    d_laps = driver_data[dn]["laps"]

    max_speeds: list[float] = []
    zone_labels: list[str] = []

    for field, label in speed_zones:
        vals = [lap[field] for lap in d_laps if lap.get(field) is not None]
        if vals:
            max_speeds.append(max(vals))
            zone_labels.append(label)
            has_any_speed = True
        else:
            max_speeds.append(0)
            zone_labels.append(label)

    fig_speed.add_trace(go.Bar(
        x=zone_labels,
        y=max_speeds,
        name=acronym,
        marker_color=color,
        hovertemplate="%{y:.1f} km/h<extra></extra>",
    ))

# Add session best as a reference trace with driver/team labels
if session_max_speeds:
    ref_labels = [label for _, label in speed_zones]
    ref_values = [session_max_speeds.get(label, 0) for label in ref_labels]
    ref_hover = [
        f"{v:.1f} km/h — {session_speed_holder.get(label, '?')}<extra></extra>"
        for label, v in zip(ref_labels, ref_values)
    ]
    fig_speed.add_trace(go.Bar(
        x=ref_labels,
        y=ref_values,
        name="Session Best",
        marker_color="#44DD44",
        hovertemplate=ref_hover,
        text=[session_speed_holder.get(label, "") for label in ref_labels],
        textposition="outside",
        textfont=dict(color="#44DD44", size=10),
    ))

if not has_any_speed:
    st.info("No speed trap data available.")
else:
    # Tight y-axis (exclude zero placeholders from range calculation)
    all_speed_vals = [
        v for trace in fig_speed.data for v in trace.y if v > 0
    ]
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

sector_data: list[dict] = []  # {acronym, s1, s2, s3, total, color}

for d in selected_drivers:
    dn = d["driver_number"]
    acronym = d.get("name_acronym", "???")
    color = driver_colors[dn]
    d_laps = driver_data[dn]["laps"]

    # Find fastest lap with complete sector data
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
        sector_data.append({
            "acronym": acronym,
            "s1": s1,
            "s2": s2,
            "s3": s3,
            "total": s1 + s2 + s3,
            "color": color,
        })

if not sector_data:
    st.info("No sector time data available.")
else:
    acronyms = [sd["acronym"] for sd in sector_data]

    fig_sectors = go.Figure()

    fig_sectors.add_trace(go.Bar(
        x=acronyms,
        y=[sd["s1"] for sd in sector_data],
        name="S1",
        marker_color="#FF3333",
        hovertemplate="S1: %{y:.3f}s<extra></extra>",
    ))
    fig_sectors.add_trace(go.Bar(
        x=acronyms,
        y=[sd["s2"] for sd in sector_data],
        name="S2",
        marker_color="#FFC700",
        hovertemplate="S2: %{y:.3f}s<extra></extra>",
    ))
    fig_sectors.add_trace(go.Bar(
        x=acronyms,
        y=[sd["s3"] for sd in sector_data],
        name="S3",
        marker_color="#9933FF",
        hovertemplate="S3: %{y:.3f}s<extra></extra>",
    ))

    # Total time annotations above bars
    for sd in sector_data:
        fig_sectors.add_annotation(
            x=sd["acronym"],
            y=sd["total"],
            text=format_lap_time(sd["total"]),
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
