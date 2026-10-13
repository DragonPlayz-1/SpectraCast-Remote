"""Local web service for the SpectraCast command center.

The service is deliberately local-first: it keeps the TV identity on the
machine that can reach the TV, serves the browser UI from the same origin, and
exposes only the small command API the interface needs.  A loopback listener is
the default.  ``--lan`` is an explicit opt-in for phones and tablets on the
same home network.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import logging
import socket
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from aiohttp import WSMsgType, web

from .device import SpectraCastDevice, SpectraCastDeviceManager
from .discovery import SpectraCastDiscovery
from .errors import SpectraCastError, SpectraCastNotConnected, SpectraCastPairingError
from .identity import FileIdentityStore
from .models import SpectraCastConnectionState, SpectraCastState

LOGGER = logging.getLogger("spectracast.server")
PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parents[1]
DEFAULT_DATA_DIR = Path(".spectradata")
DEFAULT_PORT = 8765
APP_LINKS = {
    "netflix": "netflix://",
    "youtube": "https://www.youtube.com",
    "disney+": "https://www.disneyplus.com",
    "disney": "https://www.disneyplus.com",
    "spotify": "spotify://",
    "prime video": "https://app.primevideo.com",
    "prime": "https://app.primevideo.com",
}


@dataclass(frozen=True, slots=True)
class SpectraCastServerConfig:
    """Runtime options for the local web service."""

    host: str = "127.0.0.1"
    port: int = DEFAULT_PORT
    tv_host: str | None = None
    tv_name: str = "Living Room TV"
    data_dir: Path = DEFAULT_DATA_DIR
    demo: bool = False
    auto_open: bool = True


class SpectraCastService:
    """Coordinate one TV facade and the browser-facing event stream."""

    def __init__(self, config: SpectraCastServerConfig) -> None:
        """Create a service without opening sockets or touching the TV."""
        self.config = config
        self.manager = SpectraCastDeviceManager()
        self.device: SpectraCastDevice | None = None
        self._voice_session: Any = None
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._discovery_lock = asyncio.Lock()

    async def start(self) -> None:
        """Prepare a configured endpoint without forcing a network connection."""
        if self.config.tv_host:
            self.configure_device(self.config.tv_host, self.config.tv_name)

    def configure_device(self, host: str, name: str | None = None) -> SpectraCastDevice:
        """Register a manually supplied TV endpoint."""
        host = _clean_host(host)
        if self.device is not None and self.device.host == host:
            return self.device
        if self.device is not None:
            self.device.disconnect()
        device = SpectraCastDevice(
            host,
            device_id=f"tv-{host}",
            name=name or self.config.tv_name,
            identity_store=FileIdentityStore(self.config.data_dir),
            enable_voice=True,
        )
        device.add_state_callback(self._on_state_changed)
        self.device = self.manager.register(device)
        self._publish_nowait({"type": "device", "device": _device_payload(device)})
        return device

    async def discover(self, timeout: float = 2.5) -> tuple[dict[str, Any], ...]:
        """Find TV endpoints on the local network and register the first one."""
        if self.config.demo:
            return (self._demo_device_payload(),)
        async with self._discovery_lock:
            discovered = await SpectraCastDiscovery().discover(timeout)
            payload = tuple(_discovered_payload(item) for item in discovered)
            if payload and self.device is None:
                first = payload[0]
                self.configure_device(first["host"], first["name"])
            return payload

    async def ensure_device(self) -> SpectraCastDevice:
        """Return the selected TV, discovering one when no host was configured."""
        if self.device is not None:
            return self.device
        found = await self.discover()
        if not found:
            raise SpectraCastPairingError(
                "No TV was found. Keep the TV and this computer on the same Wi-Fi, "
                "or start SpectraCast with --tv-host YOUR_TV_IP."
            )
        if self.device is None:
            raise SpectraCastPairingError("A TV was discovered but could not be selected")
        return self.device

    async def start_pairing(self) -> dict[str, Any]:
        """Begin the pairing handshake and return the selected endpoint."""
        if self.config.demo:
            return self._demo_status()
        device = await self.ensure_device()
        await device.start_pairing()
        return self.status()

    async def finish_pairing(self, code: str) -> dict[str, Any]:
        """Complete pairing with the six-character code shown on the TV."""
        if self.config.demo:
            return self._demo_status(connected=True)
        device = await self.ensure_device()
        await device.finish_pairing(code)
        await device.connect()
        return self.status()

    async def connect(self) -> dict[str, Any]:
        """Connect with the stored identity, without requiring a new pairing."""
        if self.config.demo:
            return self._demo_status(connected=True)
        device = await self.ensure_device()
        await device.connect()
        return self.status()

    def disconnect(self) -> dict[str, Any]:
        """Close the active connection and leave the identity intact."""
        if self.device is not None:
            self.device.disconnect()
        self._voice_session = None
        return self.status()

    async def send_key(self, key: int | str, direction: int | str = "SHORT") -> dict[str, Any]:
        """Send a named Android TV key to the selected screen."""
        action_name = str(key)
        if self.config.demo:
            return self._demo_status(last_action=action_name)
        device = await self._connected_device()
        device.send_key_command(key, direction)
        return self.status(last_action=action_name)

    async def launch_app(self, app: str) -> dict[str, Any]:
        """Open a known app or a caller-supplied deep link/app id."""
        link = APP_LINKS.get(app.strip().lower(), app.strip())
        if self.config.demo:
            return self._demo_status(last_action=f"Opening {app}")
        device = await self._connected_device()
        device.launch_app(link)
        return self.status(last_action=f"Opening {app}")

    async def send_text(self, text: str) -> dict[str, Any]:
        """Send text to the active TV input field."""
        if self.config.demo:
            return self._demo_status(last_action="Text sent")
        device = await self._connected_device()
        device.send_text(text)
        return self.status(last_action="Text sent")

    async def voice(self, action: str) -> dict[str, Any]:
        """Start or end a voice session when the device supports it."""
        if self.config.demo:
            return self._demo_status(last_action="Voice ready")
        device = await self._connected_device()
        if action == "start":
            self._voice_session = await device.start_voice()
            return self.status(last_action="Voice session started")
        if action == "end":
            if self._voice_session is not None:
                self._voice_session.end()
                self._voice_session = None
            return self.status(last_action="Voice session ended")
        raise ValueError("voice action must be start or end")

    async def _connected_device(self) -> SpectraCastDevice:
        device = await self.ensure_device()
        if not device.is_connected:
            await device.connect()
        if not device.is_connected:
            raise SpectraCastNotConnected("The selected TV is not ready")
        return device

    def status(self, *, last_action: str | None = None) -> dict[str, Any]:
        """Return a JSON-safe status snapshot for the browser."""
        if self.config.demo:
            return self._demo_status(last_action=last_action)
        state = self.device.state if self.device is not None else None
        payload: dict[str, Any] = {
            "ok": True,
            "connected": bool(state and state.available),
            "connection": state.connection.value if state else SpectraCastConnectionState.DISCONNECTED.value,
            "device": _state_device_payload(state),
            "volume": state.volume.level if state and state.volume else None,
            "volume_max": state.volume.maximum if state and state.volume else None,
            "muted": state.volume.muted if state and state.volume else False,
            "current_app": state.current_app if state else None,
            "last_error": state.last_error if state else None,
        }
        if last_action:
            payload["last_action"] = last_action
        return payload

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        """Register an event queue for one browser connection."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=20)
        self._subscribers.add(queue)
        queue.put_nowait({"type": "status", "status": self.status()})
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Remove a browser event queue."""
        self._subscribers.discard(queue)

    def _on_state_changed(self, state: SpectraCastState) -> None:
        self._publish_nowait({"type": "state", "status": self.status()})

    def _publish_nowait(self, event: dict[str, Any]) -> None:
        for queue in tuple(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
                queue.put_nowait(event)

    def _demo_device_payload(self) -> dict[str, Any]:
        """Return deterministic device data for screenshots and smoke tests."""
        return {
            "id": "demo-living-room",
            "name": "Living Room TV",
            "host": "demo.local",
            "ip": "192.168.1.42",
            "model": "SpectraCast Display · 4K HDR",
            "room": "Living room",
        }

    def _demo_status(self, *, connected: bool = True, last_action: str | None = None) -> dict[str, Any]:
        payload = {
            "ok": True,
            "connected": connected,
            "connection": "connected" if connected else "disconnected",
            "device": self._demo_device_payload(),
            "volume": 34,
            "volume_max": 100,
            "muted": False,
            "current_app": "YouTube",
            "last_error": None,
        }
        if last_action:
            payload["last_action"] = last_action
        return payload


SERVICE_KEY: web.AppKey[SpectraCastService] = web.AppKey("spectracast")
STATIC_DIR_KEY: web.AppKey[Path] = web.AppKey("static_dir")


def create_app(service: SpectraCastService) -> web.Application:
    """Build the aiohttp application used by the CLI and integration tests."""
    app = web.Application(middlewares=[_error_middleware])
    app[SERVICE_KEY] = service
    app[STATIC_DIR_KEY] = _static_dir()
    app.router.add_get("/api/health", _health)
    app.router.add_get("/api/status", _status)
    app.router.add_get("/api/devices", _devices)
    app.router.add_post("/api/discover", _discover)
    app.router.add_post("/api/pair/start", _pair_start)
    app.router.add_post("/api/pair", _pair_finish)
    app.router.add_post("/api/session/connect", _connect)
    app.router.add_post("/api/session/disconnect", _disconnect)
    app.router.add_post("/api/remote/key", _key)
    app.router.add_post("/api/remote/text", _text)
    app.router.add_post("/api/apps/launch", _launch)
    app.router.add_post("/api/search", _search)
    app.router.add_post("/api/voice", _voice)
    app.router.add_get("/api/events", _events)
    app.router.add_get("/", _index)
    app.router.add_get("/{path:.*}", _static)
    return app


@web.middleware
async def _error_middleware(request: web.Request, handler: Any) -> web.StreamResponse:
    """Turn expected service errors into stable JSON responses."""
    try:
        return await handler(request)
    except web.HTTPException:
        raise
    except (SpectraCastError, ValueError) as exc:
        status = 409 if isinstance(exc, SpectraCastPairingError) else 400
        return web.json_response({"ok": False, "error": str(exc)}, status=status)
    except Exception:
        LOGGER.exception("Unhandled request failure: %s %s", request.method, request.path)
        return web.json_response(
            {"ok": False, "error": "The local service encountered an unexpected error"},
            status=500,
        )


async def _health(request: web.Request) -> web.Response:
    """Report service health without requiring a TV connection."""
    service = _service(request)
    return web.json_response(
        {
            "ok": True,
            "service": "spectracast",
            "version": "0.1.0",
            "demo": service.config.demo,
        }
    )


async def _status(request: web.Request) -> web.Response:
    """Return the current TV state."""
    return web.json_response(_service(request).status())


async def _devices(request: web.Request) -> web.Response:
    """List the selected endpoint, if one exists."""
    service = _service(request)
    devices = [] if service.device is None else [_device_payload(service.device)]
    return web.json_response({"ok": True, "devices": devices})


async def _discover(request: web.Request) -> web.Response:
    """Run a bounded local-network discovery scan."""
    service = _service(request)
    payload = await service.discover(_json_number(request, "timeout", 2.5))
    return web.json_response({"ok": True, "devices": payload})


async def _pair_start(request: web.Request) -> web.Response:
    """Start the TV pairing handshake."""
    return web.json_response(await _service(request).start_pairing())


async def _pair_finish(request: web.Request) -> web.Response:
    """Finish pairing and immediately connect to the TV."""
    body = await _json_body(request)
    code = body.get("code")
    if not isinstance(code, str):
        raise ValueError("code must be a six-character hexadecimal string")
    return web.json_response(await _service(request).finish_pairing(code))


async def _connect(request: web.Request) -> web.Response:
    """Reconnect with the stored local identity."""
    return web.json_response(await _service(request).connect())


async def _disconnect(request: web.Request) -> web.Response:
    """Disconnect without deleting pairing material."""
    return web.json_response(_service(request).disconnect())


async def _key(request: web.Request) -> web.Response:
    """Dispatch one remote key command."""
    body = await _json_body(request)
    key = body.get("key")
    direction = body.get("direction", "SHORT")
    if not isinstance(key, (str, int)):
        raise ValueError("key must be a named key or numeric key code")
    if not isinstance(direction, (str, int)):
        raise ValueError("direction must be SHORT, START_LONG, or END_LONG")
    return web.json_response(await _service(request).send_key(key, direction))


async def _text(request: web.Request) -> web.Response:
    """Send text to the current TV input field."""
    body = await _json_body(request)
    text = body.get("text")
    if not isinstance(text, str) or not text:
        raise ValueError("text must be a non-empty string")
    return web.json_response(await _service(request).send_text(text))


async def _launch(request: web.Request) -> web.Response:
    """Launch a named application or deep link."""
    body = await _json_body(request)
    app = body.get("app") or body.get("link")
    if not isinstance(app, str) or not app.strip():
        raise ValueError("app must be a non-empty application name or deep link")
    return web.json_response(await _service(request).launch_app(app))


async def _search(request: web.Request) -> web.Response:
    """Accept a browser search selection and launch its target app."""
    body = await _json_body(request)
    app = body.get("app")
    title = body.get("title")
    if not isinstance(app, str) or not app.strip():
        raise ValueError("app must be a non-empty application name")
    payload = await _service(request).launch_app(app)
    if isinstance(title, str) and title.strip():
        payload["last_action"] = f"Playing {title.strip()}"
    return web.json_response(payload)


async def _voice(request: web.Request) -> web.Response:
    """Start or end the device voice session."""
    body = await _json_body(request)
    action = body.get("action", "start")
    if not isinstance(action, str):
        raise ValueError("action must be start or end")
    return web.json_response(await _service(request).voice(action.lower()))


async def _events(request: web.Request) -> web.StreamResponse:
    """Stream state changes to a browser through a same-origin WebSocket."""
    service = _service(request)
    websocket = web.WebSocketResponse(heartbeat=25)
    await websocket.prepare(request)
    queue = service.subscribe()
    try:
        while True:
            receive_task = asyncio.create_task(websocket.receive())
            event_task = asyncio.create_task(queue.get())
            done, pending = await asyncio.wait(
                (receive_task, event_task),
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            completed = done.pop()
            message = cast(Any, completed.result())
            if isinstance(message, dict):
                await websocket.send_json(message)
                continue
            if message.type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR}:
                break
            if message.type == WSMsgType.TEXT and message.data == "ping":
                await websocket.send_str("pong")
    finally:
        service.unsubscribe(queue)
    return websocket


async def _index(request: web.Request) -> web.StreamResponse:
    """Serve the production browser entry point."""
    return await _serve_file(request, "index.html")


async def _static(request: web.Request) -> web.StreamResponse:
    """Serve hashed assets from the built frontend directory."""
    path = request.match_info.get("path", "")
    if path.startswith("api/"):
        raise web.HTTPNotFound()
    if path in {"", "index.html"} or "." not in Path(path).name:
        return await _serve_file(request, "index.html")
    return await _serve_file(request, path)


async def _serve_file(request: web.Request, relative_path: str) -> web.StreamResponse:
    static_dir: Path = request.app[STATIC_DIR_KEY]
    candidate = (static_dir / relative_path).resolve()
    if static_dir not in candidate.parents and candidate != static_dir:
        raise web.HTTPForbidden()
    if not candidate.is_file():
        raise web.HTTPNotFound()
    return web.FileResponse(candidate)


async def _json_body(request: web.Request) -> dict[str, Any]:
    """Parse a small JSON request body with a consistent client error."""
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError("request body must be valid JSON") from exc
    if not isinstance(body, dict):
        raise ValueError("request body must be a JSON object")
    return body


def _json_number(request: web.Request, name: str, default: float) -> float:
    """Read and constrain one optional query/body number."""
    raw = request.query.get(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not 0 < value <= 30:
        raise ValueError(f"{name} must be between 0 and 30")
    return value


def _service(request: web.Request) -> SpectraCastService:
    """Retrieve the application service from the request."""
    return request.app[SERVICE_KEY]


def _state_device_payload(state: SpectraCastState | None) -> dict[str, Any]:
    """Serialize a state snapshot without leaking credentials."""
    if state is None:
        return {}
    return {
        "id": state.device_id,
        "name": state.name,
        "host": state.host,
        "ip": state.host,
        "room": state.name.replace(" TV", "").replace(" tv", ""),
        "model": state.device_info.model if state.device_info else "Android TV",
        "manufacturer": state.device_info.manufacturer if state.device_info else None,
    }


def _device_payload(device: SpectraCastDevice) -> dict[str, Any]:
    """Serialize a configured facade before it has connected."""
    return {
        "id": device.device_id,
        "name": device.name,
        "host": device.host,
        "ip": device.host,
        "room": device.name.replace(" TV", "").replace(" tv", ""),
        "model": device.device_info.model if device.device_info else "Android TV",
    }


def _discovered_payload(device: Any) -> dict[str, Any]:
    """Serialize a discovery model without exposing implementation types."""
    return {
        "id": device.device_id,
        "name": device.name,
        "host": device.host,
        "ip": device.host,
        "port": device.port,
        "pairing_port": device.pairing_port,
        "mac": device.mac_address,
    }


def _clean_host(host: str) -> str:
    """Reject malformed host values before they reach a socket connector."""
    value = host.strip()
    if not value or len(value) > 253 or any(char in value for char in "/\\\x00\n\r\t"):
        raise ValueError("tv_host must be a hostname or IP address")
    return value


def _static_dir() -> Path:
    """Choose the packaged build, with a source-tree fallback for development."""
    packaged = PACKAGE_ROOT / "web" / "dist"
    source_build = PROJECT_ROOT / "frontend" / "dist"
    if (packaged / "index.html").is_file():
        return packaged
    return source_build


def _local_network_ip() -> str:
    """Find the LAN address users can open from a phone on the same Wi-Fi."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 9))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the small cross-platform CLI surface."""
    parser = argparse.ArgumentParser(
        prog="spectracast",
        description="Start the SpectraCast web remote on this computer.",
    )
    parser.add_argument("--host", default=None, help="HTTP bind address (default: 127.0.0.1; --lan uses 0.0.0.0)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"HTTP port (default: {DEFAULT_PORT})")
    parser.add_argument("--tv-host", help="TV IP address or hostname; discovery is used when omitted")
    parser.add_argument("--tv-name", default="Living Room TV", help="Friendly name for a manually configured TV")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="Protected local state directory")
    parser.add_argument(
        "--lan",
        action="store_true",
        help="Allow phones/tablets on the same network to open the remote",
    )
    parser.add_argument("--demo", action="store_true", help="Run without a TV using the interactive demo state")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser after startup")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run the local web service."""
    args = _parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")
    # LAN binding is deliberately opt-in because it exposes the local command
    # surface to every device on the current network.
    bind_host = args.host or ("0.0.0.0" if args.lan else "127.0.0.1")  # noqa: S104
    if not 1 <= args.port <= 65535:
        raise SystemExit("--port must be between 1 and 65535")
    config = SpectraCastServerConfig(
        host=bind_host,
        port=args.port,
        tv_host=args.tv_host,
        tv_name=args.tv_name,
        data_dir=args.data_dir,
        demo=args.demo,
        auto_open=not args.no_browser,
    )
    service = SpectraCastService(config)
    app = create_app(service)

    async def on_startup(_app: web.Application) -> None:
        await service.start()

    app.on_startup.append(on_startup)
    url_host = _local_network_ip() if args.lan else "127.0.0.1"
    url = f"http://{url_host}:{args.port}/"
    print(f"SpectraCast is ready at {url}", flush=True)
    if args.demo:
        print("Demo mode is active — use ?demo=1 for a deterministic showcase.", flush=True)
    if args.lan:
        print("LAN access is enabled for this local network. Stop the process when you are finished.", flush=True)
    if config.auto_open:
        asyncio.get_event_loop().call_soon(webbrowser.open, url)
    web.run_app(app, host=bind_host, port=args.port, print=None)


__all__ = ["SpectraCastServerConfig", "SpectraCastService", "create_app", "main"]
