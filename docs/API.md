# SpectraCast local API

The API is same-origin with the browser app. The default base URL is
`http://127.0.0.1:8765`; when started with `--lan`, use the host computer's LAN
address instead.

All JSON endpoints return an object with `ok: true` on success. Expected client
errors return `ok: false` and HTTP 400 or 409. Private identity material is
never returned.

## Health

```http
GET /api/health
```

```json
{
  "ok": true,
  "service": "spectracast",
  "version": "0.1.0",
  "demo": false
}
```

## Status

```http
GET /api/status
```

```json
{
  "ok": true,
  "connected": true,
  "connection": "connected",
  "device": {
    "id": "tv-192.168.1.42",
    "name": "Living Room TV",
    "host": "192.168.1.42",
    "ip": "192.168.1.42",
    "room": "Living Room",
    "model": "SHIELD Android TV",
    "manufacturer": "NVIDIA"
  },
  "volume": 34,
  "volume_max": 100,
  "muted": false,
  "current_app": "com.google.android.youtube.tv",
  "last_error": null
}
```

`connection` is one of `disconnected`, `connecting`, `pairing`, or `connected`.

## Discovery

```http
POST /api/discover
content-type: application/json

{"timeout": 2.5}
```

The timeout is optional and bounded to 30 seconds. The response contains a
deduplicated `devices` array with `id`, `name`, `host`, `port`, `pairing_port`,
and optional `mac` fields.

## Pairing

Start the pairing handshake first:

```http
POST /api/pair/start
```

The TV displays a six-character hexadecimal code. Finish the exchange:

```http
POST /api/pair
content-type: application/json

{"code":"A1B2C3"}
```

The service validates the code locally before sending the derived secret. On
success it connects immediately and returns the normal status shape.

## Sessions

```http
POST /api/session/connect
POST /api/session/disconnect
```

Connect uses the stored local identity. Disconnect closes sockets but does not
delete pairing state.

## Remote commands

### Key

```http
POST /api/remote/key
content-type: application/json

{"key":"DPAD_UP","direction":"SHORT"}
```

Accepted directions are `SHORT`, `START_LONG`, and `END_LONG`. Keys can be
named Android key codes such as `HOME`, `BACK`, `ENTER`, `VOLUME_UP`, or numeric
wire values.

### Text

```http
POST /api/remote/text
content-type: application/json

{"text":"hello from SpectraCast"}
```

### Apps

```http
POST /api/apps/launch
content-type: application/json

{"app":"Netflix"}
```

Known names resolve to safe deep links. A caller may also provide a deep link
or package id. Search selections use the same app launcher:

```http
POST /api/search
content-type: application/json

{"title":"Planet Earth III","app":"Netflix"}
```

## Voice

```http
POST /api/voice
content-type: application/json

{"action":"start"}
```

Use `{"action":"end"}` to close the active session. Voice capability depends
on the TV's negotiated protocol features. Audio is intentionally not buffered
or persisted by the service.

## Events WebSocket

```text
GET /api/events
```

The server sends an initial `status` event, then state changes:

```json
{
  "type": "state",
  "status": {"connected": true, "connection": "connected"}
}
```

Clients can send `ping` and receive `pong`. Reconnect with a short backoff when
the local service restarts or the network changes.
