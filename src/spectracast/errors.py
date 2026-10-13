"""Exceptions raised by the SpectraCast backend adapter."""

from __future__ import annotations


class SpectraCastError(Exception):
    """Base class for all adapter errors."""


class SpectraCastConnectionError(SpectraCastError):
    """The adapter could not establish or keep a device connection."""


class SpectraCastNotConnected(SpectraCastConnectionError):
    """A command was requested without an active device connection."""


class SpectraCastAuthenticationError(SpectraCastConnectionError):
    """The device rejected the stored client identity."""


class SpectraCastPairingError(SpectraCastError):
    """The pairing handshake could not be completed."""


class SpectraCastIdentityError(SpectraCastError):
    """The local client identity is missing, malformed, or cannot be stored."""


class SpectraCastInvalidCommand(ValueError, SpectraCastError):
    """A command contains an unsupported key, direction, or value."""


class SpectraCastDiscoveryError(SpectraCastError):
    """Device discovery is unavailable or failed."""
