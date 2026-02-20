"""Data source selection for the F1 dashboard."""

from __future__ import annotations

from enum import Enum

import streamlit as st


class DataSource(str, Enum):
    """Supported data source backends."""

    OPENF1 = "OpenF1"
    FASTF1 = "FastF1"


def fastf1_available() -> bool:
    """Return True if the fastf1 package is importable."""
    try:
        import fastf1  # noqa: F401

        return True
    except ImportError:
        return False


def get_active_source() -> DataSource:
    """Return the currently selected data source from session state."""
    value = st.session_state.get("data_source", DataSource.OPENF1.value)
    try:
        return DataSource(value)
    except ValueError:
        return DataSource.OPENF1
