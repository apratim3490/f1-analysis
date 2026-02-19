"""Championship standings models (drivers and teams)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ChampionshipDriver(BaseModel):
    """Driver championship standing entry."""

    model_config = ConfigDict(frozen=True)

    broadcast_name: str | None = None
    driver_number: int | None = None
    first_name: str | None = None
    full_name: str | None = None
    last_name: str | None = None
    meeting_key: int | None = None
    points: float | None = None
    position: int | None = None
    session_key: int | None = None
    team_name: str | None = None


class ChampionshipTeam(BaseModel):
    """Team championship standing entry."""

    model_config = ConfigDict(frozen=True)

    meeting_key: int | None = None
    points: float | None = None
    position: int | None = None
    session_key: int | None = None
    team_name: str | None = None
