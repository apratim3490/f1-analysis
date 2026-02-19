"""Session result model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SessionResult(BaseModel):
    """Final standing after a session."""

    model_config = ConfigDict(frozen=True)

    broadcast_name: str | None = None
    driver_number: int | None = None
    first_name: str | None = None
    full_name: str | None = None
    gap_to_leader: float | str | None = None
    last_name: str | None = None
    laps_completed: int | None = None
    meeting_key: int | None = None
    name_acronym: str | None = None
    position: int | None = None
    session_key: int | None = None
    status: str | None = None
    team_name: str | None = None
