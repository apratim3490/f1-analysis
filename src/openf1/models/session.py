"""Session model (practice, qualifying, sprint, race)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Session(BaseModel):
    """F1 session (practice, qualifying, sprint, race)."""

    model_config = ConfigDict(frozen=True)

    circuit_key: int | None = None
    circuit_short_name: str | None = None
    country_code: str | None = None
    country_key: int | None = None
    country_name: str | None = None
    date_end: datetime | None = None
    date_start: datetime | None = None
    gmt_offset: str | None = None
    location: str | None = None
    meeting_key: int | None = None
    session_key: int | None = None
    session_name: str | None = None
    session_type: str | None = None
    year: int | None = None
