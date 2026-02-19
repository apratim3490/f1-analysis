"""Weather data model."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Weather(BaseModel):
    """Track weather conditions (~1 min updates)."""

    model_config = ConfigDict(frozen=True)

    air_temperature: float | None = None
    date: datetime | None = None
    humidity: float | None = None
    meeting_key: int | None = None
    pressure: float | None = None
    rainfall: int | None = None
    session_key: int | None = None
    track_temperature: float | None = None
    wind_direction: int | None = None
    wind_speed: float | None = None
