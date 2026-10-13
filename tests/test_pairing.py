"""Tests for the SpectraCast pairing handshake with a fake TLS peer."""

from __future__ import annotations

import hashlib

import pytest
from cryptography import x509

from spectracast import (
    SpectraCastPairingError,
    SpectraCastPairingProtocol,
    create_identity,
)
from spectracast._protobuf import Options, OuterMessage

from .conftest import FakeTransport, frame, parse_written, peer_certificate


def wire_integer(value: int) -> bytes:
    """Encode a pairing integer the same way the TV protocol does."""
    encoded = f"{value:X}"
    return bytes.fromhex(encoded if len(encoded) % 2 == 0 else f"0{encoded}")


def expected_pairing_code(client_pem: bytes, server_pem: bytes, nonce: str) -> tuple[str, bytes]:
    """Calculate a code for the deterministic fake device exchange."""
    client = x509.load_pem_x509_certificate(client_pem).public_key().public_numbers()
    server = x509.load_pem_x509_certificate(server_pem).public_key().public_numbers()
    digest = hashlib.sha256(
        wire_integer(client.n)
        + wire_integer(client.e)
        + wire_integer(server.n)
        + wire_integer(server.e)
        + bytes.fromhex(nonce)
    ).digest()
    return f"{digest[0]:02X}{nonce}", digest


@pytest.mark.asyncio
async def test_pairing_handshake_and_secret_are_wire_compatible() -> None:
    """All pairing phases complete entirely through a fake transport."""
    client = create_identity("SpectraCast Pairing Test")
    server = create_identity("Fake TV")
    transport = FakeTransport({"ssl_object": peer_certificate(server.certificate_pem)})
    protocol = SpectraCastPairingProtocol(client, timeout=1)
    protocol.connection_made(transport)

    start_task = __import__("asyncio").create_task(protocol.start_pairing())
    await __import__("asyncio").sleep(0)
    sent = parse_written(transport.written, OuterMessage)
    assert sent[0].pairing_request.service_name == "atvremote"
    assert sent[0].pairing_request.client_name == "SpectraCast Pairing Test"

    ack = OuterMessage(protocol_version=2, status=OuterMessage.Status.STATUS_OK)
    ack.pairing_request_ack.server_name = "Fake TV"
    protocol.data_received(frame(ack))
    options = OuterMessage(protocol_version=2, status=OuterMessage.Status.STATUS_OK)
    options.options.input_encodings.add(
        type=Options.Encoding.EncodingType.ENCODING_TYPE_HEXADECIMAL,
        symbol_length=6,
    )
    protocol.data_received(frame(options))
    configuration_ack = OuterMessage(protocol_version=2, status=OuterMessage.Status.STATUS_OK)
    configuration_ack.configuration_ack.SetInParent()
    protocol.data_received(frame(configuration_ack))
    await start_task

    code, secret = expected_pairing_code(client.certificate_pem, server.certificate_pem, "ABCD")
    finish_task = __import__("asyncio").create_task(protocol.finish_pairing(code))
    await __import__("asyncio").sleep(0)
    sent = parse_written(transport.written, OuterMessage)
    assert sent[-1].secret.secret == secret
    secret_ack = OuterMessage(protocol_version=2, status=OuterMessage.Status.STATUS_OK)
    secret_ack.secret_ack.secret = b"ack"
    protocol.data_received(frame(secret_ack))
    result = await finish_task

    assert result.server_name == "Fake TV"
    assert result.secret == secret


@pytest.mark.asyncio
async def test_pairing_rejects_a_wrong_code_before_sending_secret() -> None:
    """A typo is rejected locally and never reaches the fake TV."""
    client = create_identity("SpectraCast Pairing Test")
    server = create_identity("Fake TV")
    transport = FakeTransport({"ssl_object": peer_certificate(server.certificate_pem)})
    protocol = SpectraCastPairingProtocol(client)
    protocol.connection_made(transport)

    with pytest.raises(SpectraCastPairingError, match="does not match"):
        await protocol.finish_pairing("00ABCD")
    assert transport.written == b""
