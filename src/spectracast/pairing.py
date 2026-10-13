"""Pairing handshake for a SpectraCast device."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
from dataclasses import dataclass
from typing import Any

from cryptography import x509
from google.protobuf.message import DecodeError

from ._protobuf import Options, OuterMessage
from .errors import SpectraCastPairingError
from .framing import SpectraCastFramedProtocol
from .identity import SpectraCastIdentity

LOGGER = logging.getLogger(__name__)
PAIRING_TIMEOUT = 10.0
# This is the established wire service name. It is kept private because the
# public API is intentionally SpectraCast-branded.
_WIRE_SERVICE_NAME = "atvremote"


@dataclass(frozen=True, slots=True)
class SpectraCastPairingResult:
    """Result of a successful pairing handshake."""

    server_name: str | None = None
    secret: bytes | None = None


class SpectraCastPairingProtocol(SpectraCastFramedProtocol):
    """Drive the protobuf pairing state machine over an injected transport."""

    def __init__(
        self,
        identity: SpectraCastIdentity,
        *,
        loop: asyncio.AbstractEventLoop | None = None,
        timeout: float = PAIRING_TIMEOUT,
    ) -> None:
        """Initialize a pairing protocol using in-memory identity material."""
        super().__init__(loop=loop)
        self._identity = identity
        self._timeout = timeout
        self._start_waiter: asyncio.Future[SpectraCastPairingResult] | None = None
        self._finish_waiter: asyncio.Future[SpectraCastPairingResult] | None = None
        self._server_name: str | None = None
        self._expected_secret: bytes | None = None

    async def start_pairing(self) -> None:
        """Run the initialization and configuration phases."""
        self._ensure_transport()
        if self._start_waiter is not None:
            raise SpectraCastPairingError("Pairing is already in progress")
        self._start_waiter = self._loop.create_future()
        message = _new_message()
        message.pairing_request.client_name = self._identity.client_name
        message.pairing_request.service_name = _WIRE_SERVICE_NAME
        self.send_message(message)
        try:
            await self._wait_for(self._start_waiter)
        finally:
            self._start_waiter = None

    async def finish_pairing(self, pairing_code: str) -> SpectraCastPairingResult:
        """Validate the displayed code and complete the secret exchange."""
        self._ensure_transport()
        code = _validate_pairing_code(pairing_code)
        if self._finish_waiter is not None:
            raise SpectraCastPairingError("Pairing is already being finalized")

        server_certificate = self._server_certificate()
        expected_secret = _compute_pairing_secret(self._identity.certificate_pem, server_certificate, code)
        self._expected_secret = expected_secret
        self._finish_waiter = self._loop.create_future()
        message = _new_message()
        message.secret.secret = expected_secret
        # Do not put the derived pairing secret in debug logs.
        self.send_message(message, log_message=False)
        try:
            return await self._wait_for(self._finish_waiter)
        finally:
            self._finish_waiter = None
            self._expected_secret = None

    def connection_lost(self, exc: Exception | None) -> None:
        """Fail any pending phase when the pairing socket closes."""
        error = SpectraCastPairingError("Pairing connection was lost")
        for waiter in (self._start_waiter, self._finish_waiter):
            if waiter is not None and not waiter.done():
                waiter.set_exception(error)
        super().connection_lost(exc)

    def _handle_message(self, raw_message: bytes) -> None:
        """Advance the pairing state machine for one device message."""
        message = OuterMessage()
        try:
            message.ParseFromString(raw_message)
        except DecodeError as exc:
            self._fail_pending(SpectraCastPairingError("Could not parse pairing response"))
            LOGGER.debug("Could not parse SpectraCast pairing message: %s", exc)
            return

        if message.status != OuterMessage.Status.STATUS_OK:
            self._fail_pending(SpectraCastPairingError(f"Device rejected pairing with status {message.status}"))
            return

        response = _new_message()
        if message.HasField("pairing_request_ack"):
            self._server_name = message.pairing_request_ack.server_name or None
            response.options.preferred_role = Options.RoleType.ROLE_TYPE_INPUT
            encoding = response.options.input_encodings.add()
            encoding.type = Options.Encoding.EncodingType.ENCODING_TYPE_HEXADECIMAL
            encoding.symbol_length = 6
            self.send_message(response)
        elif message.HasField("options"):
            response.configuration.client_role = Options.RoleType.ROLE_TYPE_INPUT
            response.configuration.encoding.type = Options.Encoding.EncodingType.ENCODING_TYPE_HEXADECIMAL
            response.configuration.encoding.symbol_length = 6
            self.send_message(response)
        elif message.HasField("configuration_ack"):
            if self._start_waiter is not None and not self._start_waiter.done():
                self._start_waiter.set_result(SpectraCastPairingResult())
        elif message.HasField("secret_ack"):
            if self._finish_waiter is not None and not self._finish_waiter.done():
                self._finish_waiter.set_result(
                    SpectraCastPairingResult(server_name=self._server_name, secret=self._expected_secret)
                )
        else:
            self._fail_pending(SpectraCastPairingError("Unexpected message during pairing"))

    async def _wait_for(self, waiter: asyncio.Future[SpectraCastPairingResult]) -> SpectraCastPairingResult:
        """Wait for a phase response, disconnect, or a bounded timeout."""
        done, _pending = await asyncio.wait(
            (waiter, self.connection_lost_future),
            timeout=self._timeout,
            return_when=asyncio.FIRST_COMPLETED,
        )
        if not done:
            if not waiter.done():
                waiter.cancel()
            self.close()
            raise SpectraCastPairingError(f"No pairing response within {self._timeout} seconds")
        if waiter in done:
            return waiter.result()
        raise SpectraCastPairingError("Pairing connection was lost")

    def _fail_pending(self, error: SpectraCastPairingError) -> None:
        """Reject the active phase and close a malformed or rejected handshake."""
        for waiter in (self._start_waiter, self._finish_waiter):
            if waiter is not None and not waiter.done():
                waiter.set_exception(error)
        self.close()

    def _ensure_transport(self) -> None:
        if self.transport is None or self.transport.is_closing():
            raise SpectraCastPairingError("Pairing transport is not connected")

    def _server_certificate(self) -> bytes:
        """Extract the peer certificate from a TLS or fake transport."""
        transport = self.transport
        if transport is None or transport.is_closing():
            raise SpectraCastPairingError("Pairing transport is not connected")
        ssl_object = transport.get_extra_info("ssl_object")
        if ssl_object is None or not hasattr(ssl_object, "getpeercert"):
            raise SpectraCastPairingError("Pairing transport did not provide a peer certificate")
        certificate = ssl_object.getpeercert(True)
        if not isinstance(certificate, bytes) or not certificate:
            raise SpectraCastPairingError("Pairing peer certificate is empty")
        return certificate


def _new_message() -> OuterMessage:
    """Create a protocol-v2 success envelope."""
    message = OuterMessage()
    message.protocol_version = 2
    message.status = OuterMessage.Status.STATUS_OK
    return message


def _validate_pairing_code(pairing_code: str) -> str:
    """Validate and normalize the six-character hexadecimal code."""
    if not isinstance(pairing_code, str) or len(pairing_code) != 6:
        raise SpectraCastPairingError("Pairing code must be exactly 6 hexadecimal characters")
    try:
        bytes.fromhex(pairing_code)
    except ValueError as exc:
        raise SpectraCastPairingError("Pairing code must be hexadecimal") from exc
    return pairing_code.upper()


def _compute_pairing_secret(client_certificate_pem: bytes, server_certificate_der: bytes, pairing_code: str) -> bytes:
    """Compute the protocol's four-byte nonce-bound pairing secret."""
    try:
        client_certificate = x509.load_pem_x509_certificate(client_certificate_pem)
        server_certificate = x509.load_der_x509_certificate(server_certificate_der)
        client_modulus, client_exponent = _rsa_numbers(client_certificate)
        server_modulus, server_exponent = _rsa_numbers(server_certificate)
    except (ValueError, TypeError, AttributeError) as exc:
        raise SpectraCastPairingError("Pairing certificates are not usable RSA certificates") from exc

    digest = hashlib.sha256(
        _wire_integer(client_modulus)
        + _wire_integer(client_exponent)
        + _wire_integer(server_modulus)
        + _wire_integer(server_exponent)
        + bytes.fromhex(pairing_code[2:])
    ).digest()
    if not hmac.compare_digest(digest[:1], bytes.fromhex(pairing_code[:2])):
        raise SpectraCastPairingError(f"Pairing code does not match the device: {pairing_code}")
    return digest


def _rsa_numbers(certificate: x509.Certificate) -> tuple[int, int]:
    """Get RSA public numbers while giving non-RSA keys a clean error."""
    public_numbers: Any = certificate.public_key().public_numbers()  # type: ignore[union-attr]
    return public_numbers.n, public_numbers.e


def _wire_integer(value: int) -> bytes:
    """Encode the minimum even-length hexadecimal representation used on the wire."""
    encoded = f"{value:X}"
    if len(encoded) % 2:
        encoded = f"0{encoded}"
    return bytes.fromhex(encoded)


__all__ = ["PAIRING_TIMEOUT", "SpectraCastPairingProtocol", "SpectraCastPairingResult"]
