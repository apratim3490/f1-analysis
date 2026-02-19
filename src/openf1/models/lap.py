"""Lap telemetry model."""

from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict


class Lap(BaseModel):
    """Individual lap data with sector times and speeds."""

    model_config = ConfigDict(frozen=True)

    date_start: datetime | None = None
    driver_number: int | None = None
    duration_sector_1: float | None = None
    duration_sector_2: float | None = None
    duration_sector_3: float | None = None
    i1_speed: float | None = None
    i2_speed: float | None = None
    is_pit_out_lap: bool | None = None
    lap_duration: float | None = None
    lap_number: int | None = None
    meeting_key: int | None = None
    segments_sector_1: list[int | None] | None = None
    segments_sector_2: list[int | None] | None = None
    segments_sector_3: list[int | None] | None = None
    session_key: int | None = None
    st_speed: float | None = None

    @property
    def total_sector_time(self) -> float | None:
        """Sum of all three sector durations, or None if any is missing."""
        s1, s2, s3 = self.duration_sector_1, self.duration_sector_2, self.duration_sector_3
        if s1 is None or s2 is None or s3 is None:
            return None
        return s1 + s2 + s3

    @property
    def lap_timedelta(self) -> timedelta | None:
        """Lap duration as a timedelta, or None if missing."""
        if self.lap_duration is None:
            return None
        return timedelta(seconds=self.lap_duration)
