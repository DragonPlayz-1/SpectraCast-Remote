"""Tests for the local browser API."""

from __future__ import annotations

import pytest
from aiohttp.test_utils import TestClient, TestServer

from spectracast.server import SpectraCastServerConfig, SpectraCastService, create_app


@pytest.fixture
async def client() -> TestClient:
    """Return a demo-mode HTTP client with no network dependency."""
    service = SpectraCastService(SpectraCastServerConfig(demo=True, auto_open=False))
    app = create_app(service)
    async with TestClient(TestServer(app)) as test_client:
        yield test_client


@pytest.mark.asyncio
async def test_health_and_status_are_available_without_a_tv(client: TestClient) -> None:
    """The one-click demo can be used before a TV is paired."""
    health = await client.get("/api/health")
    status = await client.get("/api/status")

    assert health.status == 200
    assert (await health.json())["service"] == "spectracast"
    assert status.status == 200
    payload = await status.json()
    assert payload["connected"] is True
    assert payload["device"]["name"] == "Living Room TV"


@pytest.mark.asyncio
async def test_demo_command_routes_return_state(client: TestClient) -> None:
    """Key, app, search, and pairing endpoints share a stable JSON contract."""
    key = await client.post("/api/remote/key", json={"key": "HOME"})
    app = await client.post("/api/apps/launch", json={"app": "Netflix"})
    pairing = await client.post("/api/pair", json={"code": "A1B2C3"})

    assert key.status == app.status == pairing.status == 200
    assert (await key.json())["last_action"] == "HOME"
    assert (await app.json())["last_action"] == "Opening Netflix"
    assert (await pairing.json())["connected"] is True


@pytest.mark.asyncio
async def test_invalid_json_is_a_client_error(client: TestClient) -> None:
    """Malformed API requests do not become server errors."""
    response = await client.post("/api/remote/key", data="not-json", headers={"Content-Type": "application/json"})

    assert response.status == 400
    assert "valid JSON" in (await response.json())["error"]


@pytest.mark.asyncio
async def test_browser_entry_point_is_served(client: TestClient) -> None:
    """The backend serves the packaged cross-device browser shell."""
    response = await client.get("/")

    assert response.status == 200
    assert "SpectraCast" in await response.text()
