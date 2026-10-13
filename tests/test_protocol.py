"""Tests for the branded remote protocol using only an in-memory transport."""

from __future__ import annotations

import pytest

from spectracast import (
    SpectraCastConnectionState,
    SpectraCastFeature,
    SpectraCastInvalidCommand,
    SpectraCastRemoteProtocol,
)
from spectracast._protobuf import RemoteDirection, RemoteKeyCode, RemoteMessage

from .conftest import FakeTransport, frame, parse_written

ALL_FEATURES = (
    SpectraCastFeature.PING
    | SpectraCastFeature.KEY
    | SpectraCastFeature.IME
    | SpectraCastFeature.VOICE
    | SpectraCastFeature.POWER
    | SpectraCastFeature.VOLUME
    | SpectraCastFeature.APP_LINK
)


def configure_message(features: SpectraCastFeature = ALL_FEATURES) -> RemoteMessage:
    """Build the first message a TV sends."""
    message = RemoteMessage()
    message.remote_configure.code1 = int(features)
    message.remote_configure.device_info.vendor = "SpectraCast TV"
    message.remote_configure.device_info.model = "Test Panel"
    message.remote_configure.device_info.app_version = "9.4.1"
    return message


def started_message(is_on: bool = True) -> RemoteMessage:
    """Build the device-ready message."""
    message = RemoteMessage()
    message.remote_start.started = is_on
    return message


def connected_protocol(enable_voice: bool = False) -> tuple[SpectraCastRemoteProtocol, FakeTransport, list]:
    """Attach a protocol to a fake transport and record state callbacks."""
    updates: list = []
    protocol = SpectraCastRemoteProtocol(
        "living-room",
        "192.0.2.20",
        "Living Room",
        enable_voice=enable_voice,
        on_state_changed=updates.append,
    )
    transport = FakeTransport()
    protocol.connection_made(transport)
    return protocol, transport, updates


def test_fragmented_handshake_updates_state_and_negotiates_features() -> None:
    """A split frame is reassembled and answered without the original library facade."""
    protocol, transport, updates = connected_protocol(enable_voice=True)
    message = configure_message()
    wire = frame(message)
    protocol.data_received(wire[:1])
    protocol.data_received(wire[1:])

    assert protocol.device_info is not None
    assert protocol.device_info.model == "Test Panel"
    assert protocol.active_features == ALL_FEATURES
    replies = parse_written(transport.written, RemoteMessage)
    assert replies[0].remote_configure.code1 == int(ALL_FEATURES)
    assert replies[0].remote_configure.device_info.package_name == "spectracast"

    protocol.data_received(frame(started_message()))

    assert protocol.state.connection is SpectraCastConnectionState.CONNECTED
    assert protocol.state.available is True
    assert protocol.is_on is True
    assert updates[-1].available is True


def test_state_messages_and_commands_round_trip() -> None:
    """Power, app, volume, key, text, and app-link messages use generated protobufs safely."""
    protocol, transport, _updates = connected_protocol()
    protocol.data_received(frame(started_message()))
    transport.written.clear()

    app = RemoteMessage()
    app.remote_ime_key_inject.app_info.app_package = "com.example.player"
    volume = RemoteMessage()
    volume.remote_set_volume_level.volume_level = 17
    volume.remote_set_volume_level.volume_max = 100
    volume.remote_set_volume_level.volume_muted = True
    protocol.data_received(frame(app) + frame(volume))

    protocol.send_key_command("POWER")
    protocol.send_key_command("POWER", "START_LONG")
    protocol.send_text("hello")
    protocol.launch_app("com.example.player")
    sent = parse_written(transport.written, RemoteMessage)

    assert protocol.current_app == "com.example.player"
    assert protocol.volume_info is not None and protocol.volume_info.level == 17
    assert sent[0].remote_key_inject.key_code == RemoteKeyCode.KEYCODE_POWER
    assert sent[0].remote_key_inject.direction == RemoteDirection.SHORT
    assert sent[1].remote_key_inject.direction == RemoteDirection.START_LONG
    assert sent[2].remote_ime_batch_edit.edit_info[0].text_field_status.value == "hello"
    assert sent[3].remote_app_link_launch_request.app_link == "market://launch?id=com.example.player"


@pytest.mark.parametrize(
    ("key_code", "direction"),
    [("not-a-key", "SHORT"), ("POWER", "sideways")],
)
def test_invalid_command_is_rejected_without_wire_output(key_code: str, direction: str) -> None:
    """Invalid command names fail before a malformed protobuf is emitted."""
    protocol, transport, _updates = connected_protocol()
    with pytest.raises(SpectraCastInvalidCommand):
        protocol.send_key_command(key_code, direction)
    assert transport.written == b""


def test_connection_loss_marks_protocol_unavailable() -> None:
    """State callbacks expose a dropped fake transport."""
    protocol, _transport, updates = connected_protocol()
    protocol.data_received(frame(started_message()))
    protocol.connection_lost(ConnectionError("test drop"))

    assert protocol.state.connection is SpectraCastConnectionState.DISCONNECTED
    assert protocol.state.available is False
    assert updates[-1].last_error == "test drop"


@pytest.mark.asyncio
async def test_ready_wait_has_a_bounded_timeout() -> None:
    """A silent transport cannot leave a connect operation hanging forever."""
    protocol, _transport, _updates = connected_protocol()
    with pytest.raises(Exception, match="did not become ready"):
        await protocol.wait_until_ready(timeout=0.001)
