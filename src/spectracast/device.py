"""High-level SpectraCast device and registry abstractions."""

from __future__ import annotations

import asyncio
import logging
import os
import ssl
import tempfile
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any, Protocol, cast

from .commands import SpectraCastCommand
from .errors import (
    SpectraCastAuthenticationError,
    SpectraCastConnectionError,
    SpectraCastError,
    SpectraCastNotConnected,
    SpectraCastPairingError,
)
from .identity import DEFAULT_CLIENT_NAME, FileIdentityStore, SpectraCastIdentityStore
from .models import (
    DiscoveredSpectraCastDevice,
    SpectraCastConnectionState,
    SpectraCastState,
)
from .pairing import SpectraCastPairingProtocol, SpectraCastPairingResult
from .protocol import SpectraCastRemoteProtocol, SpectraCastVoiceSession

DEFAULT_REMOTE_PORT = 6466
DEFAULT_PAIRING_PORT = 6467
LOGGER = logging.getLogger(__name__)
StateCallback = Callable[[SpectraCastState], None]
ProtocolFactory = Callable[[], asyncio.Protocol]


class SpectraCastConnector(Protocol):
    """Async connector interface that makes all network operations replaceable."""

    async def __call__(
        self,
        host: str,
        port: int,
        protocol_factory: ProtocolFactory,
        ssl_context: ssl.SSLContext,
    ) -> tuple[asyncio.Transport, asyncio.Protocol]:
        """Open a transport and attach a protocol."""


async def default_spectracast_connector(
    host: str,
    port: int,
    protocol_factory: ProtocolFactory,
    ssl_context: ssl.SSLContext,
) -> tuple[asyncio.Transport, asyncio.Protocol]:
    """Connect using the event loop's normal TLS stream connector."""
    return await asyncio.get_running_loop().create_connection(protocol_factory, host, port, ssl=ssl_context)


class SpectraCastDevice:
    """Pair with, connect to, and command one TV endpoint."""

    def __init__(
        self,
        host: str,
        *,
        device_id: str | None = None,
        name: str | None = None,
        port: int = DEFAULT_REMOTE_PORT,
        pairing_port: int = DEFAULT_PAIRING_PORT,
        identity_store: SpectraCastIdentityStore | None = None,
        connector: SpectraCastConnector | None = None,
        pairing_connector: SpectraCastConnector | None = None,
        client_name: str = DEFAULT_CLIENT_NAME,
        enable_ime: bool = True,
        enable_voice: bool = False,
    ) -> None:
        """Create a device facade; no socket or certificate is opened yet."""
        if not host.strip():
            raise ValueError("host cannot be empty")
        if not 1 <= port <= 65535 or not 1 <= pairing_port <= 65535:
            raise ValueError("ports must be between 1 and 65535")
        self.host = host
        self.device_id = device_id or host
        self.name = name or self.device_id
        self.port = port
        self.pairing_port = pairing_port
        self.client_name = client_name
        self.identity_store = identity_store or FileIdentityStore()
        self._connector = connector or default_spectracast_connector
        self._pairing_connector = pairing_connector or self._connector
        self._enable_ime = enable_ime
        self._enable_voice = enable_voice
        self._state = SpectraCastState(device_id=self.device_id, host=host, name=self.name)
        self._state_callbacks: list[StateCallback] = []
        self._protocol: SpectraCastRemoteProtocol | None = None
        self._pairing_protocol: SpectraCastPairingProtocol | None = None
        self._connect_lock = asyncio.Lock()

    @property
    def state(self) -> SpectraCastState:
        """Return the latest device state snapshot."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Whether the protocol is ready to accept commands."""
        return self._state.available and self._protocol is not None

    @property
    def is_on(self) -> bool | None:
        """Return the last known power state."""
        return self._state.is_on

    @property
    def current_app(self) -> str | None:
        """Return the last known foreground app."""
        return self._state.current_app

    @property
    def device_info(self):
        """Return the last reported device metadata."""
        return self._state.device_info

    @property
    def volume(self):
        """Return the last reported volume state."""
        return self._state.volume

    @property
    def volume_info(self):
        """Alias for the last reported volume state."""
        return self._state.volume

    @property
    def is_available(self) -> bool:
        """Whether the device is ready to receive commands."""
        return self._state.available

    def add_state_callback(self, callback: StateCallback) -> None:
        """Subscribe to state changes."""
        self._state_callbacks.append(callback)

    def remove_state_callback(self, callback: StateCallback) -> None:
        """Remove a state callback."""
        self._state_callbacks.remove(callback)

    def subscribe(self, callback: StateCallback) -> Callable[[], None]:
        """Add a callback and return a small unsubscribe function."""
        self.add_state_callback(callback)

        def unsubscribe() -> None:
            self.remove_state_callback(callback)

        return unsubscribe

    async def connect(self, timeout: float = 10.0) -> SpectraCastDevice:
        """Open the remote connection and wait for the device-ready message."""
        async with self._connect_lock:
            if self.is_connected:
                return self
            self.disconnect()
            self._set_state(connection=SpectraCastConnectionState.CONNECTING, last_error=None)
            try:
                identity = self.identity_store.get_or_create(self.client_name)
                ssl_context = _ssl_context_for(identity)
            except SpectraCastError as exc:
                self._connection_failed(str(exc))
                raise
            protocol_holder: list[SpectraCastRemoteProtocol] = []

            def protocol_factory() -> SpectraCastRemoteProtocol:
                protocol = SpectraCastRemoteProtocol(
                    self.device_id,
                    self.host,
                    self.name,
                    loop=asyncio.get_running_loop(),
                    enable_ime=self._enable_ime,
                    enable_voice=self._enable_voice,
                    on_state_changed=self._on_protocol_state,
                )
                protocol_holder.append(protocol)
                return protocol

            try:
                transport, created_protocol = await self._connector(self.host, self.port, protocol_factory, ssl_context)
                protocol = protocol_holder[0] if protocol_holder else cast(SpectraCastRemoteProtocol, created_protocol)
                if protocol.transport is None:
                    protocol.connection_made(transport)
                self._protocol = protocol
                await protocol.wait_until_ready(timeout)
                return self
            except ssl.SSLError as exc:
                for protocol in protocol_holder:
                    protocol.close()
                self._connection_failed(f"The device rejected the SpectraCast identity: {exc}")
                raise SpectraCastAuthenticationError("The device rejected the SpectraCast identity") from exc
            except (OSError, SpectraCastConnectionError) as exc:
                for protocol in protocol_holder:
                    protocol.close()
                self._connection_failed(str(exc) or "Could not connect to the SpectraCast device")
                if isinstance(exc, SpectraCastConnectionError):
                    raise
                raise SpectraCastConnectionError(f"Could not connect to {self.host}:{self.port}") from exc

    async def start_pairing(self, timeout: float = 10.0) -> None:
        """Open a pairing socket and complete its automatic handshake steps."""
        self.disconnect()
        self._set_state(connection=SpectraCastConnectionState.PAIRING, last_error=None, available=False)
        try:
            identity = self.identity_store.get_or_create(self.client_name)
            ssl_context = _ssl_context_for(identity)
        except SpectraCastError as exc:
            self._pairing_failed(str(exc))
            raise
        protocol_holder: list[SpectraCastPairingProtocol] = []

        def protocol_factory() -> SpectraCastPairingProtocol:
            protocol = SpectraCastPairingProtocol(identity, loop=asyncio.get_running_loop(), timeout=timeout)
            protocol_holder.append(protocol)
            return protocol

        try:
            transport, created_protocol = await self._pairing_connector(
                self.host,
                self.pairing_port,
                protocol_factory,
                ssl_context,
            )
            protocol = protocol_holder[0] if protocol_holder else cast(SpectraCastPairingProtocol, created_protocol)
            if protocol.transport is None:
                protocol.connection_made(transport)
            self._pairing_protocol = protocol
            await protocol.start_pairing()
        except (OSError, SpectraCastPairingError) as exc:
            self._pairing_failed(str(exc) or "Could not start pairing")
            if isinstance(exc, SpectraCastPairingError):
                raise
            raise SpectraCastPairingError(f"Could not connect to {self.host}:{self.pairing_port}") from exc

    async def finish_pairing(self, pairing_code: str) -> SpectraCastPairingResult:
        """Submit the six-character code shown on the TV."""
        protocol = self._pairing_protocol
        if protocol is None:
            raise SpectraCastPairingError("Pairing has not been started")
        try:
            result = await protocol.finish_pairing(pairing_code)
        except SpectraCastPairingError as exc:
            self._pairing_failed(str(exc))
            raise
        else:
            protocol.close()
            self._pairing_protocol = None
            self._set_state(connection=SpectraCastConnectionState.DISCONNECTED, available=False, last_error=None)
            return result

    async def pair(self, pairing_code: str, timeout: float = 10.0) -> SpectraCastPairingResult:
        """Run both pairing phases for callers that already have the code."""
        await self.start_pairing(timeout=timeout)
        return await self.finish_pairing(pairing_code)

    def dispatch(self, command: SpectraCastCommand) -> None:
        """Dispatch a command through the connected protocol."""
        if self._protocol is None or not self.is_connected:
            raise SpectraCastNotConnected("SpectraCast device is not ready")
        self._protocol.dispatch(command)

    def send_key_command(self, key_code: int | str, direction: str | int = "SHORT") -> None:
        """Convenience wrapper for a key command."""
        self.dispatch(SpectraCastCommand.key(key_code, direction))

    def send_key(self, key_code: int | str, direction: str | int = "SHORT") -> None:
        """Branded shorthand for :meth:`send_key_command`."""
        self.send_key_command(key_code, direction)

    def send_text(self, text: str) -> None:
        """Convenience wrapper for text input."""
        self.dispatch(SpectraCastCommand.text(text))

    def launch_app(self, app_link_or_id: str) -> None:
        """Convenience wrapper for app launching."""
        self.dispatch(SpectraCastCommand.launch_app(app_link_or_id))

    async def start_voice(self, timeout: float = 2.0) -> SpectraCastVoiceSession:
        """Start a voice session through the active protocol."""
        if self._protocol is None or not self.is_connected:
            raise SpectraCastNotConnected("SpectraCast device is not ready")
        return await self._protocol.start_voice(timeout)

    def disconnect(self) -> None:
        """Close any active remote or pairing transport."""
        if self._protocol is not None:
            self._protocol.close()
            self._protocol = None
        if self._pairing_protocol is not None:
            self._pairing_protocol.close()
            self._pairing_protocol = None
        self._set_state(connection=SpectraCastConnectionState.DISCONNECTED, available=False)

    def _on_protocol_state(self, state: SpectraCastState) -> None:
        self._state = replace(state, device_id=self.device_id, name=self.name, host=self.host)
        self._notify_state()

    def _set_state(self, **changes: Any) -> None:
        next_state = replace(self._state, **changes)
        if next_state == self._state:
            return
        self._state = next_state
        self._notify_state()

    def _notify_state(self) -> None:
        for callback in tuple(self._state_callbacks):
            try:
                callback(self._state)
            except Exception:
                LOGGER.exception("SpectraCast state callback failed")

    def _connection_failed(self, error: str) -> None:
        if self._protocol is not None:
            self._protocol.close()
            self._protocol = None
        self._set_state(connection=SpectraCastConnectionState.DISCONNECTED, available=False, last_error=error)

    def _pairing_failed(self, error: str) -> None:
        if self._pairing_protocol is not None:
            self._pairing_protocol.close()
            self._pairing_protocol = None
        self._set_state(connection=SpectraCastConnectionState.DISCONNECTED, available=False, last_error=error)


class SpectraCastDeviceManager:
    """Small in-process registry for discovered and manually configured devices."""

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._devices: dict[str, SpectraCastDevice] = {}

    def register(self, device: SpectraCastDevice) -> SpectraCastDevice:
        """Register or replace a device by stable id."""
        self._devices[device.device_id] = device
        return device

    def add_discovered(
        self,
        discovered: DiscoveredSpectraCastDevice,
        **device_options: Any,
    ) -> SpectraCastDevice:
        """Create and register a device from a discovery result."""
        device = SpectraCastDevice(
            discovered.host,
            device_id=discovered.device_id,
            name=discovered.name,
            port=discovered.port,
            pairing_port=discovered.pairing_port,
            **device_options,
        )
        return self.register(device)

    def get(self, device_id: str) -> SpectraCastDevice | None:
        """Return a registered device, if present."""
        return self._devices.get(device_id)

    def remove(self, device_id: str) -> SpectraCastDevice | None:
        """Remove and disconnect a device."""
        device = self._devices.pop(device_id, None)
        if device is not None:
            device.disconnect()
        return device

    @property
    def devices(self) -> tuple[SpectraCastDevice, ...]:
        """Return a stable snapshot of registered devices."""
        return tuple(self._devices.values())

    async def connect_all(self, timeout: float = 10.0) -> dict[str, Exception | None]:
        """Attempt every registered device and return per-device failures."""
        outcomes: dict[str, Exception | None] = {}

        async def connect_one(device: SpectraCastDevice) -> None:
            try:
                await device.connect(timeout)
            except SpectraCastError as exc:
                outcomes[device.device_id] = exc
            else:
                outcomes[device.device_id] = None

        await asyncio.gather(*(connect_one(device) for device in self._devices.values()))
        return outcomes


def _ssl_context_for(identity) -> ssl.SSLContext:
    """Build a client context from bytes without requiring permanent key files."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    with tempfile.TemporaryDirectory(prefix="spectracast-identity-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        certificate_path = temporary_root / "client.crt.pem"
        key_path = temporary_root / "client.key.pem"
        certificate_path.write_bytes(identity.certificate_pem)
        key_path.write_bytes(identity.private_key_pem)
        os.chmod(certificate_path, 0o600)
        os.chmod(key_path, 0o600)
        context.load_cert_chain(str(certificate_path), str(key_path))
    return context


__all__ = [
    "DEFAULT_PAIRING_PORT",
    "DEFAULT_REMOTE_PORT",
    "SpectraCastConnector",
    "SpectraCastDevice",
    "SpectraCastDeviceManager",
    "default_spectracast_connector",
]
