"""Tests for the HTTP transport layer."""

from __future__ import annotations

import httpx
import pytest
import respx

from openf1._http import AsyncTransport, SyncTransport
from openf1.exceptions import OpenF1APIError, OpenF1ConnectionError, OpenF1TimeoutError

BASE_URL = "https://api.openf1.org/v1"


class TestSyncTransport:
    @respx.mock
    def test_get_success(self) -> None:
        respx.get(f"{BASE_URL}/drivers").mock(
            return_value=httpx.Response(200, json=[{"driver_number": 1}])
        )
        transport = SyncTransport()
        result = transport.get("/drivers", [("session_key", "9161")])
        assert result == [{"driver_number": 1}]
        transport.close()

    @respx.mock
    def test_get_with_params(self) -> None:
        route = respx.get(f"{BASE_URL}/laps").mock(
            return_value=httpx.Response(200, json=[])
        )
        transport = SyncTransport()
        transport.get("/laps", [("session_key", "9161"), ("driver_number", "1")])
        assert route.called
        transport.close()

    @respx.mock
    def test_get_404(self) -> None:
        respx.get(f"{BASE_URL}/drivers").mock(
            return_value=httpx.Response(404, text="Not Found")
        )
        transport = SyncTransport()
        with pytest.raises(OpenF1APIError) as exc_info:
            transport.get("/drivers", [])
        assert exc_info.value.status_code == 404
        transport.close()

    @respx.mock
    def test_get_500(self) -> None:
        respx.get(f"{BASE_URL}/drivers").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        transport = SyncTransport()
        with pytest.raises(OpenF1APIError) as exc_info:
            transport.get("/drivers", [])
        assert exc_info.value.status_code == 500
        transport.close()

    @respx.mock
    def test_connection_error(self) -> None:
        respx.get(f"{BASE_URL}/drivers").mock(side_effect=httpx.ConnectError("fail"))
        transport = SyncTransport()
        with pytest.raises(OpenF1ConnectionError):
            transport.get("/drivers", [])
        transport.close()

    @respx.mock
    def test_timeout_error(self) -> None:
        respx.get(f"{BASE_URL}/drivers").mock(side_effect=httpx.ReadTimeout("timeout"))
        transport = SyncTransport()
        with pytest.raises(OpenF1TimeoutError):
            transport.get("/drivers", [])
        transport.close()


class TestAsyncTransport:
    @respx.mock
    @pytest.mark.asyncio
    async def test_get_success(self) -> None:
        respx.get(f"{BASE_URL}/drivers").mock(
            return_value=httpx.Response(200, json=[{"driver_number": 1}])
        )
        transport = AsyncTransport()
        result = await transport.get("/drivers", [("session_key", "9161")])
        assert result == [{"driver_number": 1}]
        await transport.close()

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_404(self) -> None:
        respx.get(f"{BASE_URL}/drivers").mock(
            return_value=httpx.Response(404, text="Not Found")
        )
        transport = AsyncTransport()
        with pytest.raises(OpenF1APIError) as exc_info:
            await transport.get("/drivers", [])
        assert exc_info.value.status_code == 404
        await transport.close()

    @respx.mock
    @pytest.mark.asyncio
    async def test_connection_error(self) -> None:
        respx.get(f"{BASE_URL}/drivers").mock(side_effect=httpx.ConnectError("fail"))
        transport = AsyncTransport()
        with pytest.raises(OpenF1ConnectionError):
            await transport.get("/drivers", [])
        await transport.close()

    @respx.mock
    @pytest.mark.asyncio
    async def test_timeout_error(self) -> None:
        respx.get(f"{BASE_URL}/drivers").mock(side_effect=httpx.ReadTimeout("timeout"))
        transport = AsyncTransport()
        with pytest.raises(OpenF1TimeoutError):
            await transport.get("/drivers", [])
        await transport.close()
