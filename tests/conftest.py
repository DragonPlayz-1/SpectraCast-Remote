"""Shared fake transports for SpectraCast backend tests."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from google.protobuf.internal.decoder import _DecodeVarint  # type: ignore[attr-defined]
from google.protobuf.internal.encoder import _EncodeVarint  # type: ignore[attr-defined]
from google.protobuf.message import Message

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))


def frame(message: Message | bytes) -> bytes:
    """Length-delimit a protobuf message as the TV does."""
    raw = message if isinstance(message, bytes) else message.SerializeToString()
    prefix: list[bytes] = []
    _EncodeVarint(prefix.append, len(raw))
    return b"".join(prefix) + raw


def parse_written(written: bytes | bytearray, message_type: type[Message]) -> list[Message]:
    """Parse all messages recorded by a fake transport."""
    result: list[Message] = []
    buffer = memoryview(bytes(written))
    while buffer:
        length, prefix_size = _DecodeVarint(buffer, 0)
        message = message_type()
        message.ParseFromString(bytes(buffer[prefix_size : prefix_size + length]))
        result.append(message)
        buffer = buffer[prefix_size + length :]
    return result


class FakeTransport(asyncio.Transport):
    """In-memory transport that records wire bytes and optional TLS metadata."""

    def __init__(self, extra: dict[str, Any] | None = None) -> None:
        super().__init__()
        self.written = bytearray()
        self.closed = False
        self._extra = extra or {}

    def write(self, data: bytes) -> None:
        self.written.extend(data)

    def close(self) -> None:
        self.closed = True

    def is_closing(self) -> bool:
        return self.closed

    def get_extra_info(self, name: str, default: Any = None) -> Any:
        return self._extra.get(name, default)


class ScriptedConnector:
    """Connector that attaches a protocol and delivers scripted device frames."""

    def __init__(self, *messages: Message, extra: dict[str, Any] | None = None) -> None:
        self.messages = messages
        self.extra = extra
        self.calls: list[tuple[str, int]] = []
        self.protocol: Any = None
        self.transport: FakeTransport | None = None

    async def __call__(
        self,
        host: str,
        port: int,
        protocol_factory: Any,
        ssl_context: Any,
    ) -> tuple[FakeTransport, Any]:
        _ = ssl_context
        self.calls.append((host, port))
        self.protocol = protocol_factory()
        self.transport = FakeTransport(self.extra)
        self.protocol.connection_made(self.transport)
        for message in self.messages:
            self.protocol.data_received(frame(message))
        return self.transport, self.protocol


def peer_certificate(pem: bytes) -> SimpleNamespace:
    """Make the TLS peer-certificate object expected by the pairing adapter."""
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization

    der = x509.load_pem_x509_certificate(pem).public_bytes(serialization.Encoding.DER)
    return SimpleNamespace(getpeercert=lambda _binary: der)


@pytest.fixture
def transport() -> FakeTransport:
    """Return an empty fake transport."""
    return FakeTransport()
