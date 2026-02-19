"""Race control messages model."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RaceControl(BaseModel):
    """Race control message (flags, safety cars, incidents)."""

    model_config = ConfigDict(frozen=True)

    category: str | None = None
    date: datetime | None = None
    driver_number: int | None = None
    flag: str | None = None
    lap_number: int | None = None
    meeting_key: int | None = None
    message: str | None = None
    scope: str | None = None
    sector: int | None = None
    session_key: int | None = None
