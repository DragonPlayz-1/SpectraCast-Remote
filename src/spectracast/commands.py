"""Commands accepted by the SpectraCast device adapter."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .models import SpectraCastKeyDirection


class SpectraCastCommandType(str, Enum):
    """Supported remote command families."""

    KEY = "key"
    TEXT = "text"
    LAUNCH_APP = "launch_app"


@dataclass(frozen=True, slots=True)
class SpectraCastCommand:
    """A validated, transport-independent command."""

    type: SpectraCastCommandType
    value: int | str
    direction: SpectraCastKeyDirection | str | int = SpectraCastKeyDirection.SHORT

    def __post_init__(self) -> None:
        """Normalize the command type and reject empty values early."""
        command_type = self.type
        if isinstance(command_type, str):
            try:
                command_type = SpectraCastCommandType(command_type.lower())
            except ValueError as exc:
                raise ValueError(f"Unknown SpectraCast command type: {self.type}") from exc
            object.__setattr__(self, "type", command_type)
        if not isinstance(command_type, SpectraCastCommandType):
            raise TypeError(f"Unknown SpectraCast command type: {self.type}")

        if self.type is SpectraCastCommandType.KEY:
            if not isinstance(self.value, (int, str)) or (isinstance(self.value, str) and not self.value.strip()):
                raise ValueError("A key command needs a key code or name")
            if isinstance(self.value, int) and self.value < 0:
                raise ValueError("A key code cannot be negative")
        elif not isinstance(self.value, str) or not self.value:
            raise ValueError("Text and app commands need a non-empty string")

    @classmethod
    def key(
        cls,
        key_code: int | str,
        direction: SpectraCastKeyDirection | str | int = SpectraCastKeyDirection.SHORT,
    ) -> SpectraCastCommand:
        """Build a key command."""
        return cls(SpectraCastCommandType.KEY, key_code, direction)

    @classmethod
    def text(cls, value: str) -> SpectraCastCommand:
        """Build a text-input command."""
        return cls(SpectraCastCommandType.TEXT, value)

    @classmethod
    def launch_app(cls, value: str) -> SpectraCastCommand:
        """Build an app-link command."""
        return cls(SpectraCastCommandType.LAUNCH_APP, value)
