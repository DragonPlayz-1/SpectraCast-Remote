# Third-party notices

SpectraCast is an independent local web application. It interoperates with the
Android TV Remote protocol and includes generated Python protobuf bindings for
the protocol's wire definitions under `src/spectracast/wire/`.

## Android TV Remote protocol materials

The protocol schema is based on the public Android TV Remote protocol material
and compatible implementations listed below. The generated bindings are kept
behind the private `spectracast._protobuf` module and are not part of the
SpectraCast public API.

- Android TV Remote protocol service:
  <https://play.google.com/store/apps/details?id=com.google.android.tv.remote.service>
- Google pairing protocol reference:
  <https://android.googlesource.com/platform/external/google-tv-pairing-protocol/>
- Android key code definitions:
  <https://android.googlesource.com/platform/frameworks/native/>
- Protocol documentation and interoperability references:
  <https://github.com/Aymkdn/assistant-freebox-cloud/wiki/Google-TV-(aka-Android-TV)-Remote-Control-(v2)>

Where a source implementation or schema is distributed under Apache License
2.0, the applicable notice and license terms remain applicable to that
material. A local copy of the Apache License 2.0 text is included at
[`LICENSES/Apache-2.0.txt`](LICENSES/Apache-2.0.txt), and the canonical text is
available at <https://www.apache.org/licenses/LICENSE-2.0>.

## Runtime dependencies

SpectraCast uses these open-source Python packages at runtime:

- [aiohttp](https://github.com/aio-libs/aiohttp) — local HTTP and WebSocket server
- [cryptography](https://github.com/pyca/cryptography) — certificates and RSA identity material
- [protobuf](https://github.com/protocolbuffers/protobuf) — wire message serialization
- [zeroconf](https://github.com/python-zeroconf/python-zeroconf) — local-network discovery

The frontend build uses Vite, Tailwind CSS, PostCSS, and Autoprefixer. Their
licenses are installed with the npm lockfile and remain the responsibility of
their respective authors.

SpectraCast does not include Google branding, Google account integration, or a
cloud relay.
