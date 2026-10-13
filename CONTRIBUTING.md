# Contributing to SpectraCast

Thanks for helping make local TV control calmer and more useful.

## Before you start

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[test]"
cd frontend && npm ci
```

Do not commit `.env`, `.spectradata/`, certificates, private keys, or real
network captures. Use fake transports and generated test identities instead.

## Checks

Run the smallest relevant checks during development, then run the full suite
before opening a pull request:

```sh
pytest -q
ruff check src tests
ruff format --check src tests
mypy src/spectracast
cd frontend && npm run build
```

Changes that affect the API should update `docs/API.md` and add a regression
test. Changes that affect the visual experience should include a demo-mode
check and, when useful, an updated screenshot.

## Pull requests

- Keep one focused change per pull request.
- Explain the user-visible result and how it was verified.
- Call out platform-specific behavior for Windows, macOS, iOS, and Android.
- Preserve the local-first security boundary.
- Never claim a physical-TV behavior was tested if only a fake transport was
  used.
