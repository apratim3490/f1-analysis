"""Car location on track model (~3.7 Hz)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Location(BaseModel):
    """3D position of a car on track."""

    model_config = ConfigDict(frozen=True)

    date: datetime | None = None
    driver_number: int | None = None
    meeting_key: int | None = None
    session_key: int | None = None
    x: float | None = None
    y: float | None = None
    z: float | None = None
