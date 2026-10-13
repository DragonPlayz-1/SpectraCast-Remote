# Security policy

## Supported versions

The latest `main` branch is the supported development version. Security fixes
are applied to the latest tagged release when releases are published.

## Safe deployment defaults

SpectraCast is designed for a trusted home network:

1. The HTTP service binds to `127.0.0.1` by default.
2. Use `--lan` only when a phone or tablet needs access.
3. Do not port-forward the service or place it behind a public reverse proxy
   without adding authentication, TLS, and rate limiting.
4. Keep `.spectradata/` private. It contains the client certificate and private
   key used to authenticate to paired TVs.

The service never intentionally logs private keys, pairing PINs, derived
secrets, or voice payloads. Do not include `.env`, `.spectradata`, logs, or
packet captures in a bug report.

## Reporting a vulnerability

Please do not open a public issue for an unpatched security vulnerability. Use
the repository's private security contact when one is configured, or contact a
maintainer directly with:

- a short impact summary,
- affected version or commit,
- reproducible steps or a minimal proof of concept,
- and a suggested mitigation if known.

Allow reasonable time for a fix before public disclosure.
