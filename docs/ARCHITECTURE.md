# SpectraCast architecture

## Boundaries

SpectraCast has three deliberately small boundaries:

1. **Browser shell** — a responsive Vite/Tailwind bundle with no certificate
   access and no direct socket access to the TV.
2. **Local service** — an aiohttp server that owns discovery, pairing,
   identity storage, command validation, and state events.
3. **Device transport** — length-delimited protobuf messages over the Android TV
   Remote TLS channels.

```text
frontend/src/main.js
        │ relative JSON + WebSocket calls
        ▼
spectracast.server
        │ SpectraCastService
        ├── SpectraCastDevice
        │     ├── SpectraCastRemoteProtocol
        │     ├── SpectraCastPairingProtocol
        │     └── FileIdentityStore
        └── SpectraCastDiscovery
        │
        ▼
Android TV Remote Service
```

## Connection lifecycle

1. The service starts with no TV socket open.
2. Discovery finds an endpoint, or `--tv-host` selects one explicitly.
3. Pairing creates or loads one local RSA identity and negotiates the TV's
   hexadecimal input format.
4. The six-character TV code is validated against both certificates before a
   secret is sent.
5. A remote connection negotiates supported features and publishes immutable
   `SpectraCastState` snapshots.
6. API commands are converted into branded command objects and then wire
   messages. Invalid values fail before transport writes.
7. State callbacks fan out to WebSocket subscribers. The browser can reconnect
   without knowing anything about the protocol.

## Storage boundary

`MemoryIdentityStore` is used by tests and short-lived integrations. The CLI
uses `FileIdentityStore`, which stores a versioned JSON container below
`.spectradata/`. The certificate and key remain inside that local service
boundary; the browser sees only device metadata and state.

## Why a local service?

Browser security models are intentionally not suitable for handing a private
client certificate to JavaScript or opening arbitrary TLS sockets to a TV. A
local service makes the product work from Safari and Android browsers while
keeping the sensitive protocol operations on one trusted host.

## Extension points

- `SpectraCastDiscoverySource` can be replaced by a platform-specific scanner.
- `SpectraCastConnector` makes network tests deterministic.
- `MemoryIdentityStore` supports ephemeral deployments.
- `SpectraCastDeviceManager` can hold multiple rooms when multi-device UI is
  added.
- The browser API is relative and can be mounted behind a local reverse proxy.
