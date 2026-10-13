"""SpectraCast backend adapter for Android TV Remote protocol devices."""

from .commands import SpectraCastCommand, SpectraCastCommandType
from .device import (
    DEFAULT_PAIRING_PORT,
    DEFAULT_REMOTE_PORT,
    SpectraCastConnector,
    SpectraCastDevice,
    SpectraCastDeviceManager,
    default_spectracast_connector,
)
from .discovery import (
    SPECTRACAST_SERVICE_TYPE,
    SpectraCastDiscovery,
    SpectraCastDiscoverySource,
    StaticSpectraCastDiscovery,
    ZeroconfSpectraCastDiscovery,
)
from .errors import (
    SpectraCastAuthenticationError,
    SpectraCastConnectionError,
    SpectraCastDiscoveryError,
    SpectraCastError,
    SpectraCastIdentityError,
    SpectraCastInvalidCommand,
    SpectraCastNotConnected,
    SpectraCastPairingError,
)
from .identity import (
    DEFAULT_CLIENT_NAME,
    FileIdentityStore,
    MemoryIdentityStore,
    SpectraCastIdentity,
    SpectraCastIdentityStore,
    create_identity,
)
from .models import (
    DiscoveredSpectraCastDevice,
    SpectraCastConnectionState,
    SpectraCastDeviceInfo,
    SpectraCastKeyDirection,
    SpectraCastState,
    SpectraCastVolume,
)
from .pairing import (
    PAIRING_TIMEOUT,
    SpectraCastPairingProtocol,
    SpectraCastPairingResult,
)
from .protocol import (
    VOICE_CHUNK_MIN_SIZE,
    VOICE_CHUNK_SIZE,
    SpectraCastFeature,
    SpectraCastRemoteProtocol,
    SpectraCastVoiceSession,
)

__all__ = [
    "DEFAULT_CLIENT_NAME",
    "DEFAULT_PAIRING_PORT",
    "DEFAULT_REMOTE_PORT",
    "PAIRING_TIMEOUT",
    "SPECTRACAST_SERVICE_TYPE",
    "VOICE_CHUNK_MIN_SIZE",
    "VOICE_CHUNK_SIZE",
    "DiscoveredSpectraCastDevice",
    "FileIdentityStore",
    "MemoryIdentityStore",
    "SpectraCastAuthenticationError",
    "SpectraCastCommand",
    "SpectraCastCommandType",
    "SpectraCastConnectionError",
    "SpectraCastConnectionState",
    "SpectraCastConnector",
    "SpectraCastDevice",
    "SpectraCastDeviceInfo",
    "SpectraCastDeviceManager",
    "SpectraCastDiscovery",
    "SpectraCastDiscoveryError",
    "SpectraCastDiscoverySource",
    "SpectraCastError",
    "SpectraCastFeature",
    "SpectraCastIdentity",
    "SpectraCastIdentityError",
    "SpectraCastIdentityStore",
    "SpectraCastInvalidCommand",
    "SpectraCastKeyDirection",
    "SpectraCastNotConnected",
    "SpectraCastPairingError",
    "SpectraCastPairingProtocol",
    "SpectraCastPairingResult",
    "SpectraCastRemoteProtocol",
    "SpectraCastState",
    "SpectraCastVoiceSession",
    "SpectraCastVolume",
    "StaticSpectraCastDiscovery",
    "ZeroconfSpectraCastDiscovery",
    "create_identity",
    "default_spectracast_connector",
]
