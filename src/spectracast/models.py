"""Public data models used by the SpectraCast backend."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType


class SpectraCastConnectionState(str, Enum):
    """Lifecycle state of a SpectraCast device connection."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    PAIRING = "pairing"
    CONNECTED = "connected"


class SpectraCastKeyDirection(str, Enum):
    """How a key event is delivered to the device."""

    SHORT = "SHORT"
    START_LONG = "START_LONG"
    END_LONG = "END_LONG"


@dataclass(frozen=True, slots=True)
class SpectraCastDeviceInfo:
    """Metadata reported by a connected TV."""

    manufacturer: str
    model: str
    software_version: str

    @property
    def sw_version(self) -> str:
        """Short spelling for callers migrating from the wire model."""
        return self.software_version


@dataclass(frozen=True, slots=True)
class SpectraCastVolume:
    """Volume state reported by a connected TV."""

    level: int
    maximum: int
    muted: bool

    @property
    def max(self) -> int:
        """Compatibility-friendly spelling for the volume maximum."""
        return self.maximum


@dataclass(frozen=True, slots=True)
class SpectraCastState:
    """Immutable snapshot of everything known about a device."""

    device_id: str
    name: str
    host: str
    connection: SpectraCastConnectionState = SpectraCastConnectionState.DISCONNECTED
    available: bool = False
    is_on: bool | None = None
    current_app: str | None = None
    device_info: SpectraCastDeviceInfo | None = None
    volume: SpectraCastVolume | None = None
    voice_enabled: bool = False
    last_error: str | None = None

    @property
    def is_available(self) -> bool:
        """Whether commands can currently be sent."""
        return self.available

    @property
    def volume_info(self) -> SpectraCastVolume | None:
        """Alias used by callers that prefer the protocol terminology."""
        return self.volume


@dataclass(frozen=True, slots=True)
class DiscoveredSpectraCastDevice:
    """A device endpoint returned by a discovery source."""

    device_id: str
    host: str
    name: str
    port: int = 6466
    pairing_port: int = 6467
    mac_address: str | None = None
    properties: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate endpoint data and make properties immutable."""
        if not self.device_id.strip():
            raise ValueError("device_id cannot be empty")
        if not self.host.strip():
            raise ValueError("host cannot be empty")
        if not 1 <= self.port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        if not 1 <= self.pairing_port <= 65535:
            raise ValueError("pairing_port must be between 1 and 65535")
        object.__setattr__(self, "properties", MappingProxyType(dict(self.properties)))
