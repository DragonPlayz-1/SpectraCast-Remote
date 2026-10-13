# Troubleshooting checklist

## Start with a deterministic smoke test

```sh
python -m spectracast --demo --no-browser
```

If the demo page loads, the Python environment, packaged frontend, and HTTP
server are healthy. Add `?demo=1` if you are using a development frontend.

## Check the service

```sh
curl http://127.0.0.1:8765/api/health
curl http://127.0.0.1:8765/api/status
```

The first command should return `"ok": true`. The second may show
`connected: false` until a TV is paired.

## Check network visibility

```sh
python -m spectracast --lan --no-browser
```

Open the printed LAN URL from the phone. If it fails, use the host computer's
LAN address instead of `localhost`, check the OS firewall, and verify that the
Wi-Fi network does not enable client isolation.

## Check discovery

```sh
curl -X POST http://127.0.0.1:8765/api/discover \
  -H 'content-type: application/json' \
  -d '{"timeout":5}'
```

If the list is empty, use `--tv-host` with the TV's IP address. The service
uses TCP `6467` for pairing and TCP `6466` for commands.

## Reset a pairing

Stop SpectraCast, remove `.spectradata/`, and start again. Do not remove the
directory while a service is actively pairing.

## Collecting a safe report

Include the operating system, Python version, SpectraCast version, API health
response, and a redacted service log. Remove IP addresses if they are private,
and never include `.env`, `.spectradata`, PEM files, pairing codes, or packet
captures.
