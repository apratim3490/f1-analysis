"""Meeting (Grand Prix weekend) model."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Meeting(BaseModel):
    """Grand Prix weekend or test event."""

    model_config = ConfigDict(frozen=True)

    circuit_key: int | None = None
    circuit_short_name: str | None = None
    country_code: str | None = None
    country_key: int | None = None
    country_name: str | None = None
    date_start: datetime | None = None
    gmt_offset: str | None = None
    location: str | None = None
    meeting_key: int | None = None
    meeting_name: str | None = None
    meeting_official_name: str | None = None
    year: int | None = None
