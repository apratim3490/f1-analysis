"""Driver information model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Driver(BaseModel):
    """Driver info for a specific session."""

    model_config = ConfigDict(frozen=True)

    broadcast_name: str | None = None
    country_code: str | None = None
    driver_number: int | None = None
    first_name: str | None = None
    full_name: str | None = None
    headshot_url: str | None = None
    last_name: str | None = None
    meeting_key: int | None = None
    name_acronym: str | None = None
    session_key: int | None = None
    team_colour: str | None = None
    team_name: str | None = None
