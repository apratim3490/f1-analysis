"""Team radio model."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TeamRadio(BaseModel):
    """Driver-team radio communication."""

    model_config = ConfigDict(frozen=True)

    date: datetime | None = None
    driver_number: int | None = None
    meeting_key: int | None = None
    recording_url: str | None = None
    session_key: int | None = None
