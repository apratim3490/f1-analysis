"""Pit stop model."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Pit(BaseModel):
    """Pit stop information."""

    model_config = ConfigDict(frozen=True)

    date: datetime | None = None
    driver_number: int | None = None
    lap_number: int | None = None
    meeting_key: int | None = None
    pit_duration: float | None = None
    session_key: int | None = None
