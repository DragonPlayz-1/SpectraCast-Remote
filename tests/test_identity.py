"""Tests for SpectraCast identity lifecycle and protected storage."""

from __future__ import annotations

import stat

import pytest

from spectracast import FileIdentityStore, MemoryIdentityStore, SpectraCastIdentityError


def test_memory_identity_is_created_once_without_exposing_key_material() -> None:
    """In-memory storage reuses one identity and keeps its representation safe."""
    store = MemoryIdentityStore()
    first = store.get_or_create("Test Remote")
    second = store.get_or_create("A different display name")

    assert first is second
    assert first.client_name == "Test Remote"
    assert "PRIVATE KEY" not in repr(first)


def test_file_identity_round_trips_with_owner_only_permissions(tmp_path) -> None:
    """A disk identity survives a new store instance and is mode restricted."""
    root = tmp_path / ".spectradata"
    first_store = FileIdentityStore(root)
    first = first_store.get_or_create("SpectraCast Test")

    second = FileIdentityStore(root).load()

    assert second == first
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert stat.S_IMODE((root / "identity.json").stat().st_mode) == 0o600


def test_malformed_file_identity_is_rejected(tmp_path) -> None:
    """Corrupt identity data does not silently create a replacement key."""
    root = tmp_path / ".spectradata"
    root.mkdir()
    (root / "identity.json").write_text('{"version": 1, "private_key": "bad"}')

    with pytest.raises(SpectraCastIdentityError):
        FileIdentityStore(root).load()
