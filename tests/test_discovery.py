"""Tests for injectable SpectraCast discovery."""

from __future__ import annotations

import pytest

from spectracast import (
    DiscoveredSpectraCastDevice,
    SpectraCastDiscovery,
    StaticSpectraCastDiscovery,
)


@pytest.mark.asyncio
async def test_injected_discovery_deduplicates_stable_device_ids() -> None:
    """A platform-independent source can drive discovery without zeroconf."""
    first = DiscoveredSpectraCastDevice("tv-1", "192.0.2.10", "Living Room")
    replacement = DiscoveredSpectraCastDevice("tv-1", "192.0.2.11", "Living Room (new address)")
    second = DiscoveredSpectraCastDevice("tv-2", "192.0.2.12", "Bedroom")
    discovery = SpectraCastDiscovery(StaticSpectraCastDiscovery([first, replacement, second]))

    devices = await discovery.discover(timeout=0.1)

    assert devices == (replacement, second)
