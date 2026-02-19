"""Interval (gap) data model."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Interval(BaseModel):
    """Real-time gap between drivers (~4 sec updates)."""

    model_config = ConfigDict(frozen=True)

    date: datetime | None = None
    driver_number: int | None = None
    gap_to_leader: float | str | None = None
    interval: float | str | None = None
    meeting_key: int | None = None
    session_key: int | None = None
