"""Starting grid model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StartingGrid(BaseModel):
    """Race starting grid position."""

    model_config = ConfigDict(frozen=True)

    broadcast_name: str | None = None
    driver_number: int | None = None
    first_name: str | None = None
    full_name: str | None = None
    last_name: str | None = None
    meeting_key: int | None = None
    name_acronym: str | None = None
    position: int | None = None
    qualifying_time: str | None = None
    session_key: int | None = None
    team_name: str | None = None
