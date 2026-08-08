$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonCandidates = @(
    (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe")
)
$python = $pythonCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $python) {
    throw "No se encontro un Python compatible para el servidor M3U local."
}

Push-Location $repo
try {
    & $python .\local_m3u_server.py --host 0.0.0.0 --port 8787
    if ($LASTEXITCODE -ne 0) {
        throw "El servidor M3U local finalizo con codigo $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
