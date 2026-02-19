"""Public client classes for the OpenF1 API."""

from __future__ import annotations

from typing import Any

from pydantic import TypeAdapter

from openf1._filters import build_query_params
from openf1._http import AsyncTransport, SyncTransport
from openf1.exceptions import OpenF1ValidationError
from openf1.models.car_data import CarData
from openf1.models.championship import ChampionshipDriver, ChampionshipTeam
from openf1.models.driver import Driver
from openf1.models.interval import Interval
from openf1.models.lap import Lap
from openf1.models.location import Location
from openf1.models.meeting import Meeting
from openf1.models.overtake import Overtake
from openf1.models.pit import Pit
from openf1.models.position import Position
from openf1.models.race_control import RaceControl
from openf1.models.session import Session
from openf1.models.session_result import SessionResult
from openf1.models.starting_grid import StartingGrid
from openf1.models.stint import Stint
from openf1.models.team_radio import TeamRadio
from openf1.models.weather import Weather


def _validate_list[T](model_type: type[T], data: list[dict[str, Any]]) -> list[T]:
    """Validate a list of dicts against a Pydantic model."""
    try:
        adapter = TypeAdapter(list[model_type])
        return adapter.validate_python(data)
    except Exception as exc:
        raise OpenF1ValidationError(
            f"Failed to validate {model_type.__name__} response: {exc}"
        ) from exc


class OpenF1Client:
    """Synchronous client for the OpenF1 API.

    Usage:
        f1 = OpenF1Client()
        drivers = f1.drivers(session_key=9161)
        f1.close()

        # Or as a context manager:
        with OpenF1Client() as f1:
            laps = f1.laps(session_key=9161, driver_number=1)
    """

    def __init__(
        self,
        base_url: str = "https://api.openf1.org/v1",
        timeout: float = 30.0,
    ) -> None:
        self._transport = SyncTransport(base_url=base_url, timeout=timeout)

    def __enter__(self) -> OpenF1Client:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP connection."""
        self._transport.close()

    def _get[T](self, endpoint: str, model: type[T], **kwargs: Any) -> list[T]:
        params = build_query_params(**kwargs)
        data = self._transport.get(endpoint, params)
        return _validate_list(model, data)

    # ── Endpoints ──────────────────────────────────────────────

    def car_data(self, **kwargs: Any) -> list[CarData]:
        """Get car telemetry data (speed, throttle, brake, RPM, gear, DRS)."""
        return self._get("/car_data", CarData, **kwargs)

    def championship_drivers(self, **kwargs: Any) -> list[ChampionshipDriver]:
        """Get driver championship standings."""
        return self._get("/championship_drivers", ChampionshipDriver, **kwargs)

    def championship_teams(self, **kwargs: Any) -> list[ChampionshipTeam]:
        """Get team championship standings."""
        return self._get("/championship_teams", ChampionshipTeam, **kwargs)

    def drivers(self, **kwargs: Any) -> list[Driver]:
        """Get driver information for a session."""
        return self._get("/drivers", Driver, **kwargs)

    def intervals(self, **kwargs: Any) -> list[Interval]:
        """Get real-time gaps between drivers."""
        return self._get("/intervals", Interval, **kwargs)

    def laps(self, **kwargs: Any) -> list[Lap]:
        """Get lap data with sector times and speeds."""
        return self._get("/laps", Lap, **kwargs)

    def location(self, **kwargs: Any) -> list[Location]:
        """Get car positions on track (3D coordinates)."""
        return self._get("/location", Location, **kwargs)

    def meetings(self, **kwargs: Any) -> list[Meeting]:
        """Get Grand Prix weekends and test events."""
        return self._get("/meetings", Meeting, **kwargs)

    def overtakes(self, **kwargs: Any) -> list[Overtake]:
        """Get position change events."""
        return self._get("/overtakes", Overtake, **kwargs)

    def pit(self, **kwargs: Any) -> list[Pit]:
        """Get pit stop information."""
        return self._get("/pit", Pit, **kwargs)

    def position(self, **kwargs: Any) -> list[Position]:
        """Get driver position changes throughout a session."""
        return self._get("/position", Position, **kwargs)

    def race_control(self, **kwargs: Any) -> list[RaceControl]:
        """Get race control messages (flags, safety cars, incidents)."""
        return self._get("/race_control", RaceControl, **kwargs)

    def sessions(self, **kwargs: Any) -> list[Session]:
        """Get session information (practice, qualifying, sprint, race)."""
        return self._get("/sessions", Session, **kwargs)

    def session_result(self, **kwargs: Any) -> list[SessionResult]:
        """Get final standings after a session."""
        return self._get("/session_result", SessionResult, **kwargs)

    def starting_grid(self, **kwargs: Any) -> list[StartingGrid]:
        """Get race starting grid positions."""
        return self._get("/starting_grid", StartingGrid, **kwargs)

    def stints(self, **kwargs: Any) -> list[Stint]:
        """Get tire stint information."""
        return self._get("/stints", Stint, **kwargs)

    def team_radio(self, **kwargs: Any) -> list[TeamRadio]:
        """Get driver-team radio communications."""
        return self._get("/team_radio", TeamRadio, **kwargs)

    def weather(self, **kwargs: Any) -> list[Weather]:
        """Get track weather conditions."""
        return self._get("/weather", Weather, **kwargs)


class AsyncOpenF1Client:
    """Asynchronous client for the OpenF1 API.

    Usage:
        async with AsyncOpenF1Client() as f1:
            drivers = await f1.drivers(session_key=9161)
    """

    def __init__(
        self,
        base_url: str = "https://api.openf1.org/v1",
        timeout: float = 30.0,
    ) -> None:
        self._transport = AsyncTransport(base_url=base_url, timeout=timeout)

    async def __aenter__(self) -> AsyncOpenF1Client:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP connection."""
        await self._transport.close()

    async def _get[T](self, endpoint: str, model: type[T], **kwargs: Any) -> list[T]:
        params = build_query_params(**kwargs)
        data = await self._transport.get(endpoint, params)
        return _validate_list(model, data)

    # ── Endpoints ──────────────────────────────────────────────

    async def car_data(self, **kwargs: Any) -> list[CarData]:
        """Get car telemetry data (speed, throttle, brake, RPM, gear, DRS)."""
        return await self._get("/car_data", CarData, **kwargs)

    async def championship_drivers(self, **kwargs: Any) -> list[ChampionshipDriver]:
        """Get driver championship standings."""
        return await self._get("/championship_drivers", ChampionshipDriver, **kwargs)

    async def championship_teams(self, **kwargs: Any) -> list[ChampionshipTeam]:
        """Get team championship standings."""
        return await self._get("/championship_teams", ChampionshipTeam, **kwargs)

    async def drivers(self, **kwargs: Any) -> list[Driver]:
        """Get driver information for a session."""
        return await self._get("/drivers", Driver, **kwargs)

    async def intervals(self, **kwargs: Any) -> list[Interval]:
        """Get real-time gaps between drivers."""
        return await self._get("/intervals", Interval, **kwargs)

    async def laps(self, **kwargs: Any) -> list[Lap]:
        """Get lap data with sector times and speeds."""
        return await self._get("/laps", Lap, **kwargs)

    async def location(self, **kwargs: Any) -> list[Location]:
        """Get car positions on track (3D coordinates)."""
        return await self._get("/location", Location, **kwargs)

    async def meetings(self, **kwargs: Any) -> list[Meeting]:
        """Get Grand Prix weekends and test events."""
        return await self._get("/meetings", Meeting, **kwargs)

    async def overtakes(self, **kwargs: Any) -> list[Overtake]:
        """Get position change events."""
        return await self._get("/overtakes", Overtake, **kwargs)

    async def pit(self, **kwargs: Any) -> list[Pit]:
        """Get pit stop information."""
        return await self._get("/pit", Pit, **kwargs)

    async def position(self, **kwargs: Any) -> list[Position]:
        """Get driver position changes throughout a session."""
        return await self._get("/position", Position, **kwargs)

    async def race_control(self, **kwargs: Any) -> list[RaceControl]:
        """Get race control messages (flags, safety cars, incidents)."""
        return await self._get("/race_control", RaceControl, **kwargs)

    async def sessions(self, **kwargs: Any) -> list[Session]:
        """Get session information (practice, qualifying, sprint, race)."""
        return await self._get("/sessions", Session, **kwargs)

    async def session_result(self, **kwargs: Any) -> list[SessionResult]:
        """Get final standings after a session."""
        return await self._get("/session_result", SessionResult, **kwargs)

    async def starting_grid(self, **kwargs: Any) -> list[StartingGrid]:
        """Get race starting grid positions."""
        return await self._get("/starting_grid", StartingGrid, **kwargs)

    async def stints(self, **kwargs: Any) -> list[Stint]:
        """Get tire stint information."""
        return await self._get("/stints", Stint, **kwargs)

    async def team_radio(self, **kwargs: Any) -> list[TeamRadio]:
        """Get driver-team radio communications."""
        return await self._get("/team_radio", TeamRadio, **kwargs)

    async def weather(self, **kwargs: Any) -> list[Weather]:
        """Get track weather conditions."""
        return await self._get("/weather", Weather, **kwargs)
