"""Shared sidebar rendering for session selection."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

import streamlit as st

from .constants import PRACTICE_SESSION_TYPES
from .data import F1DataError, get_repository
from .data.source import DataSource, fastf1_available


@dataclass(frozen=True)
class SessionSelection:
    """Result of the session sidebar cascade."""

    session_key: int | str
    meeting_name: str
    session_name: str
    is_practice: bool
    drivers: list[dict]


# ── OpenF1 sidebar ──────────────────────────────────────────────────────────


def _render_openf1_sidebar() -> SessionSelection | None:
    """Render the OpenF1 year/meeting/session/driver cascade."""
    repo = get_repository()

    current_year = datetime.date.today().year
    years = list(range(current_year, 2022, -1))
    selected_year = st.sidebar.selectbox("Year", years, key="of1_year")

    try:
        meetings = repo.get_meetings(selected_year)
    except F1DataError as exc:
        st.sidebar.error(f"Failed to load meetings: {exc}")
        return None

    if not meetings:
        st.sidebar.warning("No meetings found for this year.")
        return None

    meeting_options = {
        m["meeting_name"]: m["meeting_key"]
        for m in meetings
        if m.get("meeting_name") and m.get("meeting_key")
    }
    if not meeting_options:
        st.sidebar.warning("No valid meetings found for this year.")
        return None
    selected_meeting_name = st.sidebar.selectbox(
        "Meeting", list(meeting_options.keys()), key="of1_meeting",
    )
    selected_meeting_key = meeting_options[selected_meeting_name]

    try:
        sessions = repo.get_sessions(selected_meeting_key)
    except F1DataError as exc:
        st.sidebar.error(f"Failed to load sessions: {exc}")
        return None

    if not sessions:
        st.sidebar.warning("No sessions found for this meeting.")
        return None

    session_options = {
        s["session_name"]: s
        for s in sessions
        if s.get("session_name") and s.get("session_key")
    }
    if not session_options:
        st.sidebar.warning("No valid sessions found for this meeting.")
        return None
    selected_session_name = st.sidebar.selectbox(
        "Session", list(session_options.keys()), key="of1_session",
    )
    selected_session = session_options[selected_session_name]
    selected_session_key = selected_session["session_key"]
    session_type = selected_session.get("session_type", "")
    is_practice = session_type in PRACTICE_SESSION_TYPES

    try:
        drivers = repo.get_drivers(selected_session_key)
    except F1DataError as exc:
        st.sidebar.error(f"Failed to load drivers: {exc}")
        return None

    if not drivers:
        st.sidebar.warning("No drivers found for this session.")
        return None

    return SessionSelection(
        session_key=selected_session_key,
        meeting_name=selected_meeting_name,
        session_name=selected_session_name,
        is_practice=is_practice,
        drivers=drivers,
    )


# ── FastF1 sidebar ──────────────────────────────────────────────────────────


def _render_fastf1_sidebar() -> SessionSelection | None:
    """Render the FastF1 year/event/session/driver cascade."""
    repo = get_repository()

    current_year = datetime.date.today().year
    years = list(range(current_year, 2017, -1))
    selected_year = st.sidebar.selectbox("Year", years, key="ff1_year")

    try:
        meetings = repo.get_meetings(selected_year)
    except F1DataError as exc:
        st.sidebar.error(f"Failed to load events: {exc}")
        return None

    if not meetings:
        st.sidebar.warning("No events found for this year.")
        return None

    meeting_options = {
        m["meeting_name"]: m["meeting_key"]
        for m in meetings
        if m.get("meeting_name") and m.get("meeting_key")
    }
    if not meeting_options:
        st.sidebar.warning("No valid events found for this year.")
        return None
    selected_meeting_name = st.sidebar.selectbox(
        "Event", list(meeting_options.keys()), key="ff1_event",
    )
    selected_meeting_key = meeting_options[selected_meeting_name]

    try:
        sessions = repo.get_sessions(selected_meeting_key)
    except F1DataError as exc:
        st.sidebar.error(f"Failed to load sessions: {exc}")
        return None

    if not sessions:
        st.sidebar.warning("No sessions found for this event.")
        return None

    session_options = {
        s["session_name"]: s
        for s in sessions
        if s.get("session_name") and s.get("session_key")
    }
    if not session_options:
        st.sidebar.warning("No valid sessions found for this event.")
        return None
    selected_session_name = st.sidebar.selectbox(
        "Session", list(session_options.keys()), key="ff1_session",
    )
    selected_session = session_options[selected_session_name]
    selected_session_key = selected_session["session_key"]
    session_type = selected_session.get("session_type", "")
    is_practice = session_type in PRACTICE_SESSION_TYPES

    try:
        drivers = repo.get_drivers(selected_session_key)
    except F1DataError as exc:
        st.sidebar.error(f"Failed to load drivers: {exc}")
        return None

    if not drivers:
        st.sidebar.warning("No drivers found for this session.")
        return None

    return SessionSelection(
        session_key=selected_session_key,
        meeting_name=selected_meeting_name,
        session_name=selected_session_name,
        is_practice=is_practice,
        drivers=drivers,
    )


# ── Public entry point ──────────────────────────────────────────────────────


def render_session_sidebar() -> SessionSelection | None:
    """Render year/meeting/session/driver cascade in the sidebar.

    Shows a data source toggle when FastF1 is installed. Returns a
    SessionSelection on success, or None if any step fails (callers
    should handle None by calling st.stop() themselves).
    """
    if fastf1_available():
        source = st.sidebar.radio(
            "Data Source",
            [DataSource.OPENF1.value, DataSource.FASTF1.value],
            horizontal=True,
            key="data_source",
        )
    else:
        source = DataSource.OPENF1.value
        st.session_state["data_source"] = source

    st.sidebar.divider()

    if source == DataSource.FASTF1.value:
        return _render_fastf1_sidebar()
    return _render_openf1_sidebar()
