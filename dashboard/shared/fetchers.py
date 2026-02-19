"""Cached data fetchers for the OpenF1 API."""

from __future__ import annotations

import time

import streamlit as st

from openf1 import OpenF1Client

# ── Rate limiting ────────────────────────────────────────────────────────────

_last_request_time: float = 0.0
_MIN_REQUEST_INTERVAL = 0.35  # OpenF1 allows 3 req/s; 350ms keeps us safe


def _rate_limit() -> None:
    """Sleep if needed to respect the OpenF1 API rate limit."""
    global _last_request_time
    now = time.monotonic()
    elapsed = now - _last_request_time
    if elapsed < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.monotonic()


# ── Cached fetchers ──────────────────────────────────────────────────────────


@st.cache_data(ttl=600)
def fetch_meetings(year: int) -> list[dict]:
    _rate_limit()
    with OpenF1Client() as f1:
        return [m.model_dump() for m in f1.meetings(year=year)]


@st.cache_data(ttl=600)
def fetch_sessions(meeting_key: int) -> list[dict]:
    _rate_limit()
    with OpenF1Client() as f1:
        return [s.model_dump() for s in f1.sessions(meeting_key=meeting_key)]


@st.cache_data(ttl=600)
def fetch_drivers(session_key: int) -> list[dict]:
    _rate_limit()
    with OpenF1Client() as f1:
        return [d.model_dump() for d in f1.drivers(session_key=session_key)]


@st.cache_data(ttl=600)
def fetch_laps(session_key: int, driver_number: int) -> list[dict]:
    _rate_limit()
    with OpenF1Client() as f1:
        return [lap.model_dump() for lap in f1.laps(
            session_key=session_key, driver_number=driver_number,
        )]


@st.cache_data(ttl=600)
def fetch_all_laps(session_key: int) -> list[dict]:
    _rate_limit()
    with OpenF1Client() as f1:
        return [lap.model_dump() for lap in f1.laps(session_key=session_key)]


@st.cache_data(ttl=600)
def fetch_stints(session_key: int, driver_number: int) -> list[dict]:
    _rate_limit()
    with OpenF1Client() as f1:
        return [s.model_dump() for s in f1.stints(
            session_key=session_key, driver_number=driver_number,
        )]


@st.cache_data(ttl=600)
def fetch_pits(session_key: int, driver_number: int) -> list[dict]:
    _rate_limit()
    with OpenF1Client() as f1:
        return [p.model_dump() for p in f1.pit(
            session_key=session_key, driver_number=driver_number,
        )]
