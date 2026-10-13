"""Local client identity generation and protected persistence."""

from __future__ import annotations

import base64
import contextlib
import json
import os
import stat
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from .errors import SpectraCastIdentityError

IDENTITY_VERSION = 1
DEFAULT_CLIENT_NAME = "SpectraCast Remote"


@dataclass(frozen=True, slots=True, repr=False)
class SpectraCastIdentity:
    """A client certificate and private key used for pairing and TLS."""

    client_name: str
    certificate_pem: bytes
    private_key_pem: bytes

    def __post_init__(self) -> None:
        """Validate key material before it can enter a store."""
        if not self.client_name.strip():
            raise SpectraCastIdentityError("client_name cannot be empty")
        try:
            certificate = x509.load_pem_x509_certificate(self.certificate_pem)
            private_key = serialization.load_pem_private_key(self.private_key_pem, password=None)
        except (AttributeError, ValueError, TypeError) as exc:
            raise SpectraCastIdentityError("Invalid SpectraCast certificate or private key") from exc
        if certificate.public_key().public_numbers() != private_key.public_key().public_numbers():  # type: ignore[union-attr]
            raise SpectraCastIdentityError("Certificate and private key do not match")

    def __repr__(self) -> str:
        """Avoid including private key material in diagnostics."""
        return f"SpectraCastIdentity(client_name={self.client_name!r})"


class SpectraCastIdentityStore(Protocol):
    """Storage interface used by devices; implementations can be in memory or on disk."""

    def load(self) -> SpectraCastIdentity | None:
        """Load the identity, if one has already been created."""

    def save(self, identity: SpectraCastIdentity) -> None:
        """Persist an identity."""

    def get_or_create(self, client_name: str = DEFAULT_CLIENT_NAME) -> SpectraCastIdentity:
        """Return the existing identity or create one exactly once."""


class MemoryIdentityStore:
    """An identity store suitable for tests and short-lived backend processes."""

    def __init__(self, identity: SpectraCastIdentity | None = None) -> None:
        """Initialize an empty or pre-seeded store."""
        self._identity = identity

    def load(self) -> SpectraCastIdentity | None:
        """Return the current identity without exposing mutable storage."""
        return self._identity

    def save(self, identity: SpectraCastIdentity) -> None:
        """Keep the validated identity in memory."""
        self._identity = identity

    def get_or_create(self, client_name: str = DEFAULT_CLIENT_NAME) -> SpectraCastIdentity:
        """Create a certificate/key pair only on the first request."""
        if self._identity is None:
            self._identity = create_identity(client_name)
        return self._identity


class FileIdentityStore:
    """Persist identity material in a mode-restricted ``.spectradata`` directory."""

    def __init__(self, root: str | os.PathLike[str] = ".spectradata") -> None:
        """Initialize the store; files are created lazily."""
        self.root = Path(root)
        self.path = self.root / "identity.json"

    def load(self) -> SpectraCastIdentity | None:
        """Read and validate the identity without logging secret fields."""
        if not self.path.exists():
            return None
        try:
            raw = _read_private_file(self.path)
            payload = json.loads(raw)
            if not isinstance(payload, dict) or payload.get("version") != IDENTITY_VERSION:
                raise ValueError("unsupported identity version")
            client_name = payload["client_name"]
            certificate = _decode_secret(payload["certificate"])
            private_key = _decode_secret(payload["private_key"])
            if not isinstance(client_name, str):
                raise TypeError("client_name must be a string")
            return SpectraCastIdentity(client_name, certificate, private_key)
        except SpectraCastIdentityError:
            raise
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            raise SpectraCastIdentityError(f"Cannot read identity from {self.path}") from exc

    def save(self, identity: SpectraCastIdentity) -> None:
        """Atomically save identity JSON with owner-only permissions."""
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            os.chmod(self.root, 0o700)
            payload = {
                "version": IDENTITY_VERSION,
                "client_name": identity.client_name,
                "certificate": _encode_secret(identity.certificate_pem),
                "private_key": _encode_secret(identity.private_key_pem),
            }
            encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            fd, temporary_name = tempfile.mkstemp(prefix=".identity-", suffix=".tmp", dir=self.root, text=False)
            try:
                os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
                with os.fdopen(fd, "wb") as temporary:
                    temporary.write(encoded)
                    temporary.flush()
                    os.fsync(temporary.fileno())
                os.replace(temporary_name, self.path)
                os.chmod(self.path, 0o600)
            except BaseException:
                _remove_if_present(Path(temporary_name))
                raise
        except OSError as exc:
            raise SpectraCastIdentityError(f"Cannot save identity to {self.path}") from exc

    def get_or_create(self, client_name: str = DEFAULT_CLIENT_NAME) -> SpectraCastIdentity:
        """Return a persisted identity or create and persist the first one."""
        identity = self.load()
        if identity is None:
            identity = create_identity(client_name)
            self.save(identity)
        return identity


def create_identity(client_name: str = DEFAULT_CLIENT_NAME) -> SpectraCastIdentity:
    """Generate a self-signed client certificate accepted by the TV protocol."""
    if not client_name.strip():
        raise SpectraCastIdentityError("client_name cannot be empty")
    try:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, client_name)])
        now = datetime.now(timezone.utc)  # noqa: UP017 - supports Python 3.10
        certificate = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=False)
            .add_extension(x509.SubjectAlternativeName([x509.DNSName(client_name)]), critical=False)
            .sign(key, hashes.SHA256(), default_backend())
        )
        certificate_pem = certificate.public_bytes(serialization.Encoding.PEM)
        private_key_pem = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
        return SpectraCastIdentity(client_name, certificate_pem, private_key_pem)
    except (ValueError, TypeError) as exc:
        raise SpectraCastIdentityError("Could not generate the SpectraCast client identity") from exc


def _encode_secret(value: bytes) -> str:
    """Encode binary key material for the local JSON container."""
    return base64.b64encode(value).decode("ascii")


def _decode_secret(value: Any) -> bytes:
    """Decode a strict base64 field from the identity container."""
    if not isinstance(value, str):
        raise TypeError("identity secret must be a string")
    return base64.b64decode(value.encode("ascii"), validate=True)


def _read_private_file(path: Path) -> bytes:
    """Read a file without following symlinks when the platform supports it."""
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        return os.read(fd, os.stat(fd).st_size)
    finally:
        os.close(fd)


def _remove_if_present(path: Path) -> None:
    """Best-effort cleanup for an interrupted atomic write."""
    with contextlib.suppress(FileNotFoundError):
        path.unlink()


__all__ = [
    "DEFAULT_CLIENT_NAME",
    "FileIdentityStore",
    "MemoryIdentityStore",
    "SpectraCastIdentity",
    "SpectraCastIdentityStore",
    "create_identity",
]
