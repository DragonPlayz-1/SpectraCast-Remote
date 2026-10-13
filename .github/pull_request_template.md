## User-visible result

<!-- What can someone do after this change that they could not do before? -->

## Checks run

- [ ] `pytest -q`
- [ ] `ruff check src tests`
- [ ] `ruff format --check src tests`
- [ ] `mypy src/spectracast`
- [ ] `cd frontend && npm run build`

## Security / privacy review

- [ ] No secrets, `.env`, `.spectradata`, certificates, or private keys included
- [ ] LAN exposure and browser storage behavior remain intentional
