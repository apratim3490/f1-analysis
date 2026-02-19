"""Shared sidebar rendering for session selection."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

import streamlit as st

from openf1.exceptions import OpenF1Error

from .constants import PRACTICE_SESSION_TYPES
from .fetchers import fetch_drivers, fetch_meetings, fetch_sessions


@dataclass(frozen=True)
class SessionSelection:
    """Result of the session sidebar cascade."""

    session_key: int
    meeting_name: str
    session_name: str
    is_practice: bool
    drivers: list[dict]


def render_session_sidebar() -> SessionSelection | None:
    """Render year/meeting/session/driver cascade in the sidebar.

    Returns a SessionSelection on success, or None (with st.stop()) on failure.
    """
    # Year selector
    current_year = datetime.date.today().year
    years = list(range(current_year, 2022, -1))
    selected_year = st.sidebar.selectbox("Year", years)

    # Meetings
    try:
        meetings = fetch_meetings(selected_year)
    except OpenF1Error as exc:
        st.sidebar.error(f"Failed to load meetings: {exc}")
        st.stop()
        return None  # unreachable, but helps type checkers

    if not meetings:
        st.sidebar.warning("No meetings found for this year.")
        st.stop()
        return None

    meeting_options = {
        m["meeting_name"]: m["meeting_key"]
        for m in meetings
        if m.get("meeting_name") and m.get("meeting_key")
    }
    if not meeting_options:
        st.sidebar.warning("No valid meetings found for this year.")
        st.stop()
        return None
    selected_meeting_name = st.sidebar.selectbox("Meeting", list(meeting_options.keys()))
    selected_meeting_key = meeting_options[selected_meeting_name]

    # Sessions
    try:
        sessions = fetch_sessions(selected_meeting_key)
    except OpenF1Error as exc:
        st.sidebar.error(f"Failed to load sessions: {exc}")
        st.stop()
        return None

    if not sessions:
        st.sidebar.warning("No sessions found for this meeting.")
        st.stop()
        return None

    session_options = {
        s["session_name"]: s
        for s in sessions
        if s.get("session_name") and s.get("session_key")
    }
    if not session_options:
        st.sidebar.warning("No valid sessions found for this meeting.")
        st.stop()
        return None
    selected_session_name = st.sidebar.selectbox("Session", list(session_options.keys()))
    selected_session = session_options[selected_session_name]
    selected_session_key = selected_session["session_key"]
    session_type = selected_session.get("session_type", "")
    is_practice = session_type in PRACTICE_SESSION_TYPES

    # Drivers
    try:
        drivers = fetch_drivers(selected_session_key)
    except OpenF1Error as exc:
        st.sidebar.error(f"Failed to load drivers: {exc}")
        st.stop()
        return None

    if not drivers:
        st.sidebar.warning("No drivers found for this session.")
        st.stop()
        return None

    return SessionSelection(
        session_key=selected_session_key,
        meeting_name=selected_meeting_name,
        session_name=selected_session_name,
        is_practice=is_practice,
        drivers=drivers,
    )
