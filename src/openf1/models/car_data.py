"""Car telemetry data model (~3.7 Hz sample rate)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CarData(BaseModel):
    """Vehicle telemetry snapshot."""

    model_config = ConfigDict(frozen=True)

    brake: int | None = None
    date: datetime | None = None
    driver_number: int | None = None
    drs: int | None = None
    meeting_key: int | None = None
    n_gear: int | None = None
    rpm: int | None = None
    session_key: int | None = None
    speed: int | None = None
    throttle: int | None = None
