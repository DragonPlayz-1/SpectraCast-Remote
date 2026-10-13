"""Discovery interfaces and an optional zeroconf implementation."""

from __future__ import annotations

import asyncio
from typing import Protocol

from .errors import SpectraCastDiscoveryError
from .models import DiscoveredSpectraCastDevice

SPECTRACAST_SERVICE_TYPE = "_androidtvremote2._tcp.local."


class SpectraCastDiscoverySource(Protocol):
    """Injectable discovery source used by tests or platform integrations."""

    async def discover(self, timeout: float) -> list[DiscoveredSpectraCastDevice]:
        """Return endpoints observed during the scan window."""


class StaticSpectraCastDiscovery:
    """A deterministic source useful for local configuration and unit tests."""

    def __init__(self, devices: list[DiscoveredSpectraCastDevice] | tuple[DiscoveredSpectraCastDevice, ...]) -> None:
        """Store a snapshot of endpoints."""
        self._devices = tuple(devices)

    async def discover(self, timeout: float) -> list[DiscoveredSpectraCastDevice]:
        """Return the snapshot without waiting on the network."""
        _ = timeout
        return list(self._devices)


class SpectraCastDiscovery:
    """Discover devices from an injected source or optional zeroconf support."""

    def __init__(self, source: SpectraCastDiscoverySource | None = None) -> None:
        """Initialize discovery with a platform source when supplied."""
        self._source = source

    async def discover(self, timeout: float = 3.0) -> tuple[DiscoveredSpectraCastDevice, ...]:
        """Scan and return deduplicated endpoints."""
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        source = self._source or ZeroconfSpectraCastDiscovery()
        devices = await source.discover(timeout)
        unique: dict[str, DiscoveredSpectraCastDevice] = {}
        for device in devices:
            unique[device.device_id] = device
        return tuple(unique.values())


class ZeroconfSpectraCastDiscovery:
    """Discover the TV service when the optional ``zeroconf`` package is installed."""

    async def discover(self, timeout: float) -> list[DiscoveredSpectraCastDevice]:
        """Browse the established TV remote service type."""
        try:
            from zeroconf import ServiceStateChange
            from zeroconf.asyncio import (
                AsyncServiceBrowser,
                AsyncServiceInfo,
                AsyncZeroconf,
            )
        except ImportError as exc:
            raise SpectraCastDiscoveryError(
                "Zeroconf discovery needs the optional 'zeroconf' package or an injected source"
            ) from exc

        loop = asyncio.get_running_loop()
        devices: dict[str, DiscoveredSpectraCastDevice] = {}
        tasks: set[asyncio.Task[None]] = set()
        zeroconf = AsyncZeroconf()

        async def resolve(service_name: str) -> None:
            info = AsyncServiceInfo(SPECTRACAST_SERVICE_TYPE, service_name)
            if not await info.async_request(zeroconf.zeroconf, int(timeout * 1000)):
                return
            addresses = info.parsed_scoped_addresses()
            if not addresses:
                return
            properties = {_decode_property(key): _decode_property(value) for key, value in info.properties.items()}
            device_id = service_name.rstrip(".")
            devices[device_id] = DiscoveredSpectraCastDevice(
                device_id=device_id,
                host=addresses[0],
                name=properties.get("name", device_id),
                port=info.port or 6466,
                pairing_port=6467,
                mac_address=properties.get("mac") or properties.get("mac_address"),
                properties=properties,
            )

        def on_service_state_change(
            _zeroconf: object,
            _service_type: str,
            service_name: str,
            state_change: ServiceStateChange,
        ) -> None:
            if state_change not in {ServiceStateChange.Added, ServiceStateChange.Updated}:
                return
            task = loop.create_task(resolve(service_name))
            tasks.add(task)
            task.add_done_callback(tasks.discard)

        browser = AsyncServiceBrowser(
            zeroconf.zeroconf,
            [SPECTRACAST_SERVICE_TYPE],
            handlers=[on_service_state_change],
        )
        try:
            await asyncio.sleep(timeout)
            if tasks:
                await asyncio.gather(*tuple(tasks), return_exceptions=True)
        finally:
            await browser.async_cancel()
            await zeroconf.async_close()
        return list(devices.values())


def _decode_property(value: object) -> str:
    """Decode zeroconf TXT keys and values without failing discovery."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


__all__ = [
    "SPECTRACAST_SERVICE_TYPE",
    "SpectraCastDiscovery",
    "SpectraCastDiscoverySource",
    "StaticSpectraCastDiscovery",
    "ZeroconfSpectraCastDiscovery",
]
