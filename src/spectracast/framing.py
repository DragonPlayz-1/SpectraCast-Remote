"""Length-delimited protobuf framing for fake and real transports."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Protocol, cast

if TYPE_CHECKING:
    from google.protobuf.message import Message


LOGGER = logging.getLogger(__name__)
DEFAULT_MAX_FRAME_SIZE = 1024 * 1024


class SpectraCastTransport(Protocol):
    """Small transport surface needed by the protocol adapter."""

    def write(self, data: bytes) -> None:
        """Write bytes to the peer."""

    def close(self) -> None:
        """Close the transport."""

    def is_closing(self) -> bool:
        """Return whether the transport is closing."""

    def get_extra_info(self, name: str, default: object = None) -> object:
        """Return transport-specific metadata."""


class _IncompleteVarint(Exception):
    """Internal marker for a length prefix split across reads."""


class SpectraCastFramedProtocol(asyncio.Protocol):
    """Decode and encode the protocol's varint-prefixed protobuf messages."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop | None = None,
        max_frame_size: int = DEFAULT_MAX_FRAME_SIZE,
    ) -> None:
        """Initialize an empty framed protocol."""
        self._loop = loop or _event_loop()
        self._max_frame_size = max_frame_size
        self.transport: SpectraCastTransport | None = None
        self._buffer = bytearray()
        self._connection_lost: asyncio.Future[Exception | None] = self._loop.create_future()

    @property
    def connection_lost_future(self) -> asyncio.Future[Exception | None]:
        """Future completed when the underlying transport closes."""
        return self._connection_lost

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        """Attach the transport supplied by asyncio or a fake connector."""
        self.transport = cast(SpectraCastTransport, transport)

    def connection_lost(self, exc: Exception | None) -> None:
        """Complete the connection future exactly once."""
        if not self._connection_lost.done():
            self._connection_lost.set_result(exc)
        self.transport = None

    def data_received(self, data: bytes) -> None:
        """Buffer arbitrary read fragments and handle each complete frame."""
        if not data:
            return
        self._buffer.extend(data)
        while self._buffer:
            try:
                message_size, prefix_size = _decode_varint(self._buffer)
            except _IncompleteVarint:
                return
            except ValueError as exc:
                LOGGER.debug("Invalid SpectraCast frame length: %s", exc)
                self._buffer.clear()
                self._close_transport()
                return

            if message_size > self._max_frame_size:
                LOGGER.debug("SpectraCast frame exceeds %s bytes", self._max_frame_size)
                self._buffer.clear()
                self._close_transport()
                return
            frame_end = prefix_size + message_size
            if len(self._buffer) < frame_end:
                return
            raw_message = bytes(self._buffer[prefix_size:frame_end])
            del self._buffer[:frame_end]
            self._handle_message(raw_message)

    def _handle_message(self, raw_message: bytes) -> None:
        """Handle a complete raw message in a subclass."""

    def send_message(self, message: Message, *, log_message: bool = True) -> bool:
        """Frame and buffer a protobuf message; return whether it was written."""
        transport = self.transport
        if transport is None or transport.is_closing():
            return False
        if log_message:
            LOGGER.debug("Sending SpectraCast message %s", message.DESCRIPTOR.full_name)
        raw_message = message.SerializeToString()
        if len(raw_message) > self._max_frame_size:
            raise ValueError("protobuf message exceeds the configured frame limit")
        transport.write(_encode_varint(len(raw_message)) + raw_message)
        return True

    def close(self) -> None:
        """Close the attached transport if one exists."""
        self._close_transport()

    def _close_transport(self) -> None:
        if self.transport is not None and not self.transport.is_closing():
            self.transport.close()


def _event_loop() -> asyncio.AbstractEventLoop:
    """Get an event loop for protocols constructed by synchronous test code."""
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        policy = asyncio.get_event_loop_policy()
        try:
            return policy.get_event_loop()
        except RuntimeError:
            loop = policy.new_event_loop()
            policy.set_event_loop(loop)
            return loop


def _encode_varint(value: int) -> bytes:
    """Encode a non-negative integer as a protobuf varint."""
    if value < 0:
        raise ValueError("varints cannot encode negative values")
    output = bytearray()
    while value >= 0x80:
        output.append((value & 0x7F) | 0x80)
        value >>= 7
    output.append(value)
    return bytes(output)


def _decode_varint(buffer: bytearray | bytes) -> tuple[int, int]:
    """Decode the first varint, rejecting overlong or overflowing prefixes."""
    value = 0
    for index, byte in enumerate(buffer):
        if index >= 10 or (index == 9 and byte > 1):
            raise ValueError("varint exceeds the protobuf 64-bit limit")
        value |= (byte & 0x7F) << (7 * index)
        if not byte & 0x80:
            return value, index + 1
    raise _IncompleteVarint


__all__ = ["DEFAULT_MAX_FRAME_SIZE", "SpectraCastFramedProtocol", "SpectraCastTransport"]
