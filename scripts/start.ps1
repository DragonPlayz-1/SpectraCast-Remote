$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot ".."))
Set-Location $Root

$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) {
    throw "Python 3.10+ is required. Install it from https://www.python.org/downloads/"
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
}

& ".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
& ".venv\Scripts\python.exe" -m pip install --quiet -e .
& ".venv\Scripts\python.exe" -m spectracast --lan @args
