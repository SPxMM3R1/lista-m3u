$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonCandidates = @(
    (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe")
)
$python = $pythonCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $python) {
    throw "No se encontro un Python compatible para actualizar la lista."
}

Push-Location $repo
try {
    $status = git status --porcelain
    if ($status) {
        throw "El checkout tiene cambios locales; se cancela para no sobrescribirlos."
    }

    git fetch origin main
    if ($LASTEXITCODE -ne 0) { throw "No se pudo descargar origin/main." }
    git merge --ff-only origin/main
    if ($LASTEXITCODE -ne 0) { throw "El checkout local no pudo avanzar hasta origin/main." }

    & $python update_m3u.py
    if ($LASTEXITCODE -ne 0) { throw "El actualizador M3U fallo." }

    git add m3u.m3u epg.xml custom-hls
    git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) { exit 0 }

    git -c user.name="VibeM3U local updater" -c user.email="vibem3u-local-updater@users.noreply.github.com" commit -m "Actualiza enlaces desde Chile [skip ci]"
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el commit local." }

    git push origin main
    if ($LASTEXITCODE -ne 0) {
        git fetch origin main
        git rebase origin/main
        if ($LASTEXITCODE -ne 0) {
            git rebase --abort
            throw "El push encontro cambios simultaneos en origin/main."
        }
        git push origin main
        if ($LASTEXITCODE -ne 0) { throw "No se pudo publicar el segundo intento." }
    }
}
finally {
    Pop-Location
}
