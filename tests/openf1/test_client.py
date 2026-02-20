"""Tests for the OpenF1 client classes."""

from __future__ import annotations

import httpx
import pytest
import respx

from openf1 import AsyncOpenF1Client, Filter, OpenF1Client
from openf1.models.driver import Driver
from openf1.models.lap import Lap
from openf1.models.session import Session
from openf1.models.weather import Weather
from tests.conftest import SAMPLE_DRIVER, SAMPLE_LAP, SAMPLE_SESSION, SAMPLE_WEATHER

BASE_URL = "https://api.openf1.org/v1"


class TestOpenF1Client:
    @respx.mock
    def test_drivers(self) -> None:
        respx.get(f"{BASE_URL}/drivers").mock(
            return_value=httpx.Response(200, json=[SAMPLE_DRIVER])
        )
        with OpenF1Client() as f1:
            drivers = f1.drivers(session_key=9161)
        assert len(drivers) == 1
        assert isinstance(drivers[0], Driver)
        assert drivers[0].driver_number == 1

    @respx.mock
    def test_sessions(self) -> None:
        respx.get(f"{BASE_URL}/sessions").mock(
            return_value=httpx.Response(200, json=[SAMPLE_SESSION])
        )
        with OpenF1Client() as f1:
            sessions = f1.sessions(year=2023)
        assert len(sessions) == 1
        assert isinstance(sessions[0], Session)
        assert sessions[0].session_name == "Race"

    @respx.mock
    def test_laps_with_filter(self) -> None:
        respx.get(f"{BASE_URL}/laps").mock(
            return_value=httpx.Response(200, json=[SAMPLE_LAP])
        )
        with OpenF1Client() as f1:
            laps = f1.laps(
                session_key=9161,
                driver_number=1,
                lap_number=Filter(gte=5, lte=10),
            )
        assert len(laps) == 1
        assert isinstance(laps[0], Lap)

    @respx.mock
    def test_weather(self) -> None:
        respx.get(f"{BASE_URL}/weather").mock(
            return_value=httpx.Response(200, json=[SAMPLE_WEATHER])
        )
        with OpenF1Client() as f1:
            weather = f1.weather(session_key=9161)
        assert len(weather) == 1
        assert isinstance(weather[0], Weather)
        assert weather[0].air_temperature == 30.5

    @respx.mock
    def test_empty_response(self) -> None:
        respx.get(f"{BASE_URL}/drivers").mock(
            return_value=httpx.Response(200, json=[])
        )
        with OpenF1Client() as f1:
            drivers = f1.drivers(session_key=99999)
        assert drivers == []

    @respx.mock
    def test_context_manager(self) -> None:
        respx.get(f"{BASE_URL}/drivers").mock(
            return_value=httpx.Response(200, json=[])
        )
        with OpenF1Client() as f1:
            f1.drivers()

    @respx.mock
    def test_all_endpoint_methods_exist(self) -> None:
        """Verify all 18 endpoint methods are present."""
        client = OpenF1Client()
        endpoints = [
            "car_data", "championship_drivers", "championship_teams",
            "drivers", "intervals", "laps", "location", "meetings",
            "overtakes", "pit", "position", "race_control", "sessions",
            "session_result", "starting_grid", "stints", "team_radio", "weather",
        ]
        for endpoint in endpoints:
            assert hasattr(client, endpoint), f"Missing endpoint: {endpoint}"
            assert callable(getattr(client, endpoint))
        client.close()


class TestAsyncOpenF1Client:
    @respx.mock
    @pytest.mark.asyncio
    async def test_drivers(self) -> None:
        respx.get(f"{BASE_URL}/drivers").mock(
            return_value=httpx.Response(200, json=[SAMPLE_DRIVER])
        )
        async with AsyncOpenF1Client() as f1:
            drivers = await f1.drivers(session_key=9161)
        assert len(drivers) == 1
        assert isinstance(drivers[0], Driver)
        assert drivers[0].driver_number == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_laps_with_filter(self) -> None:
        respx.get(f"{BASE_URL}/laps").mock(
            return_value=httpx.Response(200, json=[SAMPLE_LAP])
        )
        async with AsyncOpenF1Client() as f1:
            laps = await f1.laps(
                session_key=9161,
                lap_number=Filter(gte=1),
            )
        assert len(laps) == 1
        assert isinstance(laps[0], Lap)

    @respx.mock
    @pytest.mark.asyncio
    async def test_empty_response(self) -> None:
        respx.get(f"{BASE_URL}/sessions").mock(
            return_value=httpx.Response(200, json=[])
        )
        async with AsyncOpenF1Client() as f1:
            sessions = await f1.sessions(year=9999)
        assert sessions == []
