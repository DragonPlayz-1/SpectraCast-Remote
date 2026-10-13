"""Tests for the high-level device facade and registry."""

from __future__ import annotations

import pytest

from spectracast import (
    DiscoveredSpectraCastDevice,
    MemoryIdentityStore,
    SpectraCastConnectionState,
    SpectraCastDevice,
    SpectraCastDeviceManager,
)
from spectracast._protobuf import RemoteMessage

from .conftest import ScriptedConnector, parse_written


def ready_message() -> tuple[RemoteMessage, RemoteMessage]:
    """Return a realistic configure/start pair for a fake TV."""
    configure = RemoteMessage()
    configure.remote_configure.code1 = 0x267
    configure.remote_configure.device_info.vendor = "Panel Co"
    configure.remote_configure.device_info.model = "Panel 1"
    configure.remote_configure.device_info.app_version = "1.0"
    started = RemoteMessage()
    started.remote_start.started = False
    return configure, started


@pytest.mark.asyncio
async def test_device_connects_and_dispatches_using_a_fake_connector() -> None:
    """The facade reaches a ready state without opening a physical socket."""
    connector = ScriptedConnector(*ready_message())
    device = SpectraCastDevice(
        "192.0.2.44",
        device_id="tv-living-room",
        name="Living Room",
        identity_store=MemoryIdentityStore(),
        connector=connector,
        client_name="SpectraCast Test",
    )
    updates = []
    device.add_state_callback(updates.append)

    await device.connect(timeout=1)
    device.send_key_command("HOME")

    assert connector.calls == [("192.0.2.44", 6466)]
    assert device.is_connected is True
    assert device.state.connection is SpectraCastConnectionState.CONNECTED
    assert device.state.is_on is False
    assert device.state.device_info is not None
    assert device.state.device_info.model == "Panel 1"
    sent = parse_written(connector.transport.written, RemoteMessage)
    assert sent[-1].remote_key_inject.key_code == 3
    assert updates[-1].available is True

    connector.protocol.connection_lost(None)
    assert device.state.connection is SpectraCastConnectionState.DISCONNECTED
    assert device.is_connected is False


@pytest.mark.asyncio
async def test_device_connection_failure_is_stateful() -> None:
    """A connector failure is surfaced and retained in the state snapshot."""

    async def failing_connector(*args, **kwargs):
        raise OSError("network unavailable")

    device = SpectraCastDevice(
        "192.0.2.45",
        identity_store=MemoryIdentityStore(),
        connector=failing_connector,
    )
    with pytest.raises(Exception, match="Could not connect"):
        await device.connect()

    assert device.state.connection is SpectraCastConnectionState.DISCONNECTED
    assert device.state.last_error == "network unavailable"


@pytest.mark.asyncio
async def test_discovery_results_can_be_registered_without_network() -> None:
    """The registry creates stable device facades from discovery data."""
    manager = SpectraCastDeviceManager()
    discovered = DiscoveredSpectraCastDevice(
        device_id="tv-bedroom",
        host="192.0.2.46",
        name="Bedroom",
        properties={"source": "fake"},
    )

    device = manager.add_discovered(discovered, identity_store=MemoryIdentityStore())

    assert manager.get("tv-bedroom") is device
    assert manager.devices == (device,)
    assert manager.remove("tv-bedroom") is device
    assert manager.devices == ()
