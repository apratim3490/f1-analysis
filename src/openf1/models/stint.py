"""Stint model (continuous driving period on one set of tires)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Stint(BaseModel):
    """Continuous driving stint on one compound."""

    model_config = ConfigDict(frozen=True)

    compound: str | None = None
    driver_number: int | None = None
    lap_end: int | None = None
    lap_start: int | None = None
    meeting_key: int | None = None
    session_key: int | None = None
    stint_number: int | None = None
    tyre_age_at_start: int | None = None
