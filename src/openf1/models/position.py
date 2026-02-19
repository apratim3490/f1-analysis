"""Driver position model."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Position(BaseModel):
    """Driver position change during a session."""

    model_config = ConfigDict(frozen=True)

    date: datetime | None = None
    driver_number: int | None = None
    meeting_key: int | None = None
    position: int | None = None
    session_key: int | None = None
