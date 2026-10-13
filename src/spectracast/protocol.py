"""SpectraCast-branded remote protocol built on the existing protobuf schema."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import replace
from enum import IntFlag
from typing import Any, cast
from urllib.parse import urlparse

from google.protobuf.message import DecodeError

from ._protobuf import RemoteDirection, RemoteKeyCode, RemoteMessage
from .commands import SpectraCastCommand, SpectraCastCommandType
from .errors import (
    SpectraCastConnectionError,
    SpectraCastInvalidCommand,
    SpectraCastNotConnected,
)
from .framing import SpectraCastFramedProtocol
from .models import (
    SpectraCastConnectionState,
    SpectraCastDeviceInfo,
    SpectraCastKeyDirection,
    SpectraCastState,
    SpectraCastVolume,
)

LOGGER = logging.getLogger(__name__)
TEXT_COMMAND_PREFIX = "text:"
VOICE_CHUNK_SIZE = 20 * 1024
VOICE_CHUNK_MIN_SIZE = 8 * 1024


class SpectraCastFeature(IntFlag):
    """Features negotiated with a TV on the wire."""

    PING = 2**0
    KEY = 2**1
    IME = 2**2
    VOICE = 2**3
    UNKNOWN_1 = 2**4
    POWER = 2**5
    VOLUME = 2**6
    APP_LINK = 2**9


StateCallback = Callable[[SpectraCastState], None]


class SpectraCastRemoteProtocol(SpectraCastFramedProtocol):
    """Implement the TV remote message exchange behind a branded API."""

    def __init__(
        self,
        device_id: str,
        host: str,
        name: str,
        *,
        loop: asyncio.AbstractEventLoop | None = None,
        enable_ime: bool = True,
        enable_voice: bool = False,
        on_state_changed: StateCallback | None = None,
    ) -> None:
        """Initialize a protocol instance that can be attached to any transport."""
        super().__init__(loop=loop)
        self._state = SpectraCastState(device_id=device_id, host=host, name=name)
        self._state_callbacks: list[StateCallback] = []
        if on_state_changed is not None:
            self._state_callbacks.append(on_state_changed)
        self._requested_features = (
            SpectraCastFeature.PING
            | SpectraCastFeature.KEY
            | SpectraCastFeature.POWER
            | SpectraCastFeature.VOLUME
            | SpectraCastFeature.APP_LINK
            | (SpectraCastFeature.IME if enable_ime else 0)
            | (SpectraCastFeature.VOICE if enable_voice else 0)
        )
        self._active_features = self._requested_features
        self._ready = self._loop.create_future()
        self._voice_starting = False
        self._voice_session_id: int | None = None
        self._voice_begin: asyncio.Future[int] | None = None
        self._ime_counter = 0
        self._ime_field_counter = 0

    @property
    def state(self) -> SpectraCastState:
        """Return the latest immutable state snapshot."""
        return self._state

    @property
    def is_on(self) -> bool | None:
        """Return the last known power state."""
        return self._state.is_on

    @property
    def current_app(self) -> str | None:
        """Return the last known foreground app package."""
        return self._state.current_app

    @property
    def device_info(self) -> SpectraCastDeviceInfo | None:
        """Return the last reported device metadata."""
        return self._state.device_info

    @property
    def volume_info(self) -> SpectraCastVolume | None:
        """Return the last reported volume state."""
        return self._state.volume

    @property
    def is_voice_enabled(self) -> bool:
        """Return whether voice is enabled after feature negotiation."""
        return bool(self._active_features & SpectraCastFeature.VOICE)

    @property
    def active_features(self) -> SpectraCastFeature:
        """Return the negotiated feature bit set."""
        return self._active_features

    def add_state_callback(self, callback: StateCallback) -> None:
        """Subscribe to immutable state snapshots."""
        self._state_callbacks.append(callback)

    def remove_state_callback(self, callback: StateCallback) -> None:
        """Remove a previously registered state callback."""
        self._state_callbacks.remove(callback)

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        """Mark a newly attached transport as connecting."""
        super().connection_made(transport)
        self._set_state(connection=SpectraCastConnectionState.CONNECTING, available=False, last_error=None)

    def connection_lost(self, exc: Exception | None) -> None:
        """Make loss visible and unblock any pending operation."""
        self._voice_session_id = None
        if self._voice_begin is not None and not self._voice_begin.done():
            self._voice_begin.set_exception(SpectraCastConnectionError("Voice connection was lost"))
        if not self._ready.done():
            self._ready.set_exception(SpectraCastConnectionError("SpectraCast connection was lost"))
        error_text = str(exc) if exc else None
        self._set_state(
            connection=SpectraCastConnectionState.DISCONNECTED,
            available=False,
            last_error=error_text,
        )
        super().connection_lost(exc)

    async def wait_until_ready(self, timeout: float = 10.0) -> None:
        """Wait until the device has sent its ready/power message."""
        if self._state.available:
            return
        try:
            await asyncio.wait_for(asyncio.shield(self._ready), timeout=timeout)
        except TimeoutError as exc:
            raise SpectraCastConnectionError(f"Device did not become ready within {timeout} seconds") from exc

    def dispatch(self, command: SpectraCastCommand) -> None:
        """Dispatch a transport-independent command to the TV."""
        if command.type is SpectraCastCommandType.KEY:
            self.send_key_command(command.value, command.direction)
        elif command.type is SpectraCastCommandType.TEXT:
            self.send_text(cast(str, command.value))
        elif command.type is SpectraCastCommandType.LAUNCH_APP:
            self.launch_app(cast(str, command.value))
        else:
            raise SpectraCastInvalidCommand(f"Unsupported command type: {command.type}")

    def send_key_command(
        self,
        key_code: int | str,
        direction: SpectraCastKeyDirection | str | int = SpectraCastKeyDirection.SHORT,
    ) -> None:
        """Send a key press, accepting generated enum names or numeric codes."""
        if isinstance(key_code, str) and key_code.lower().startswith(TEXT_COMMAND_PREFIX):
            self.send_text(key_code[len(TEXT_COMMAND_PREFIX) :])
            return
        self._ensure_transport()
        if isinstance(key_code, str):
            normalized_key = key_code.upper()
            if not normalized_key.startswith("KEYCODE_"):
                normalized_key = f"KEYCODE_{normalized_key}"
            try:
                key_code = RemoteKeyCode.Value(normalized_key)
            except ValueError as exc:
                raise SpectraCastInvalidCommand(f"Unknown key code: {key_code}") from exc
        if not isinstance(key_code, int) or key_code < 0:
            raise SpectraCastInvalidCommand("key_code must be a non-negative integer or enum name")

        if isinstance(direction, (SpectraCastKeyDirection, str)):
            direction_name = direction.value if isinstance(direction, SpectraCastKeyDirection) else direction.upper()
            try:
                direction = RemoteDirection.Value(direction_name)
            except ValueError as exc:
                raise SpectraCastInvalidCommand(f"Unknown key direction: {direction}") from exc
        if not isinstance(direction, int):
            raise SpectraCastInvalidCommand("direction must be an enum name or integer")
        try:
            RemoteDirection.Name(direction)
        except ValueError as exc:
            raise SpectraCastInvalidCommand(f"Unknown key direction: {direction}") from exc

        message = RemoteMessage()
        message.remote_key_inject.key_code = key_code
        message.remote_key_inject.direction = direction
        self.send_message(message)

    def send_key(
        self,
        key_code: int | str,
        direction: SpectraCastKeyDirection | str | int = SpectraCastKeyDirection.SHORT,
    ) -> None:
        """Branded shorthand for :meth:`send_key_command`."""
        self.send_key_command(key_code, direction)

    def send_text(self, text: str) -> None:
        """Send text through the TV input method."""
        self._ensure_transport()
        if not text:
            raise SpectraCastInvalidCommand("Text cannot be empty")
        end = len(text) - 1
        message = RemoteMessage()
        message.remote_ime_batch_edit.ime_counter = self._ime_counter
        message.remote_ime_batch_edit.field_counter = self._ime_field_counter
        edit = message.remote_ime_batch_edit.edit_info.add()
        edit.insert = 1
        edit.text_field_status.start = end
        edit.text_field_status.end = end
        edit.text_field_status.value = text
        self.send_message(message)

    def launch_app(self, app_link_or_id: str) -> None:
        """Launch a deep link or an app id through the remote protocol."""
        self._ensure_transport()
        if not app_link_or_id:
            raise SpectraCastInvalidCommand("App link or id cannot be empty")
        app_link = app_link_or_id if urlparse(app_link_or_id).scheme else f"market://launch?id={app_link_or_id}"
        message = RemoteMessage()
        message.remote_app_link_launch_request.app_link = app_link
        self.send_message(message)

    async def start_voice(self, timeout: float = 2.0) -> SpectraCastVoiceSession:
        """Start a voice session and return its context-manager wrapper."""
        self._ensure_transport()
        if not self.is_voice_enabled:
            raise SpectraCastInvalidCommand("Voice is not enabled for this device")
        if self._voice_starting or self._voice_session_id is not None:
            raise SpectraCastInvalidCommand("A voice session is already in progress")

        self._voice_starting = True
        self._voice_begin = self._loop.create_future()
        try:
            self.send_key_command(RemoteKeyCode.KEYCODE_SEARCH)
            session_id = await asyncio.wait_for(asyncio.shield(self._voice_begin), timeout=timeout)
            begin = RemoteMessage()
            begin.remote_voice_begin.session_id = session_id
            self.send_message(begin)
            self._voice_session_id = session_id
            return SpectraCastVoiceSession(self, session_id)
        finally:
            self._voice_starting = False
            self._voice_begin = None

    def send_voice_chunk(self, chunk: bytes, session_id: int) -> None:
        """Send PCM voice data in protocol-sized, padded chunks."""
        self._ensure_transport()
        for offset in range(0, len(chunk), VOICE_CHUNK_SIZE):
            samples = bytes(chunk[offset : offset + VOICE_CHUNK_SIZE])
            if len(samples) < VOICE_CHUNK_MIN_SIZE:
                samples = samples.ljust(VOICE_CHUNK_MIN_SIZE, b"\x00")
            message = RemoteMessage()
            message.remote_voice_payload.session_id = session_id
            message.remote_voice_payload.samples = samples
            self.send_message(message, log_message=False)

    def end_voice(self, session_id: int) -> None:
        """End a voice session on the TV."""
        self._ensure_transport()
        message = RemoteMessage()
        message.remote_voice_end.session_id = session_id
        self.send_message(message)
        if self._voice_session_id == session_id:
            self._voice_session_id = None

    def _handle_message(self, raw_message: bytes) -> None:
        """Parse a device message and update state or send its protocol reply."""
        message = RemoteMessage()
        try:
            message.ParseFromString(raw_message)
        except DecodeError as exc:
            LOGGER.debug("Could not parse SpectraCast remote message: %s", exc)
            return

        response = RemoteMessage()
        if message.HasField("remote_configure"):
            configure = message.remote_configure
            self._active_features &= SpectraCastFeature(configure.code1)
            info = SpectraCastDeviceInfo(
                manufacturer=configure.device_info.vendor,
                model=configure.device_info.model,
                software_version=configure.device_info.app_version,
            )
            self._set_state(device_info=info, voice_enabled=self.is_voice_enabled)
            response.remote_configure.code1 = int(self._active_features)
            response.remote_configure.device_info.unknown1 = 1
            response.remote_configure.device_info.unknown2 = "1"
            response.remote_configure.device_info.package_name = "spectracast"
            response.remote_configure.device_info.app_version = "1.0.0"
        elif message.HasField("remote_set_active"):
            response.remote_set_active.active = int(self._active_features)
        elif message.HasField("remote_ime_key_inject"):
            self._set_state(current_app=message.remote_ime_key_inject.app_info.app_package)
        elif message.HasField("remote_ime_batch_edit"):
            self._ime_counter = message.remote_ime_batch_edit.ime_counter
            self._ime_field_counter = message.remote_ime_batch_edit.field_counter
        elif message.HasField("remote_set_volume_level"):
            volume_message = message.remote_set_volume_level
            self._set_state(
                volume=SpectraCastVolume(
                    level=volume_message.volume_level,
                    maximum=volume_message.volume_max,
                    muted=volume_message.volume_muted,
                )
            )
        elif message.HasField("remote_start"):
            self._set_state(
                connection=SpectraCastConnectionState.CONNECTED,
                available=True,
                is_on=message.remote_start.started,
                voice_enabled=self.is_voice_enabled,
                last_error=None,
            )
            if not self._ready.done():
                self._ready.set_result(None)
        elif message.HasField("remote_ping_request"):
            response.remote_ping_response.val1 = message.remote_ping_request.val1
        elif message.HasField("remote_error"):
            self._set_state(last_error="The device reported a remote protocol error")
            LOGGER.warning("SpectraCast device reported a remote protocol error")
        elif message.HasField("remote_voice_begin"):
            if self._voice_begin is not None and not self._voice_begin.done():
                self._voice_begin.set_result(message.remote_voice_begin.session_id)
            else:
                LOGGER.debug("Ignoring unsolicited SpectraCast voice session")

        if response.ByteSize():
            self.send_message(response, log_message=False)

    def _set_state(self, **changes: Any) -> None:
        next_state = replace(self._state, **changes)
        if next_state == self._state:
            return
        self._state = next_state
        for callback in tuple(self._state_callbacks):
            try:
                callback(self._state)
            except Exception:
                LOGGER.exception("SpectraCast state callback failed")

    def _ensure_transport(self) -> None:
        if self.transport is None or self.transport.is_closing():
            raise SpectraCastNotConnected("SpectraCast device is not connected")


class SpectraCastVoiceSession:
    """Small async-context-manager wrapper for one voice session."""

    def __init__(self, protocol: SpectraCastRemoteProtocol, session_id: int) -> None:
        """Bind the session to its protocol."""
        self._protocol = protocol
        self.session_id = session_id
        self._ended = False

    async def __aenter__(self) -> SpectraCastVoiceSession:  # noqa: PYI034 - Python 3.10 compatible
        """Return this active session."""
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        """End the session when leaving the context."""
        self.end()

    def send_chunk(self, chunk: bytes) -> None:
        """Send a PCM chunk for this voice session."""
        if self._ended:
            raise SpectraCastNotConnected("Voice session has ended")
        self._protocol.send_voice_chunk(chunk, self.session_id)

    def end(self) -> None:
        """End this session once, safely."""
        if not self._ended:
            self._ended = True
            self._protocol.end_voice(self.session_id)


__all__ = [
    "VOICE_CHUNK_MIN_SIZE",
    "VOICE_CHUNK_SIZE",
    "SpectraCastFeature",
    "SpectraCastRemoteProtocol",
    "SpectraCastVoiceSession",
]
