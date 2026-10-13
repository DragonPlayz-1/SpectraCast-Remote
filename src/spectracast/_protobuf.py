"""Private access to the generated SpectraCast wire definitions.

The generated modules are shipped inside the package so an installed
SpectraCast service is self-contained.  They are intentionally not part of the
public API; callers should use the branded models and command objects instead.
"""

from .wire.polo_pb2 import Options, OuterMessage  # type: ignore[attr-defined]
from .wire.remotemessage_pb2 import RemoteDirection, RemoteKeyCode, RemoteMessage  # type: ignore[attr-defined]

__all__ = ["Options", "OuterMessage", "RemoteDirection", "RemoteKeyCode", "RemoteMessage"]
