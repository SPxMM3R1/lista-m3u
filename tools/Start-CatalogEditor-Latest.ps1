param(
    [string]$VibeM3UPath
)

# Inicia el generador de catalogos con la ultima version publicada.
# Actualiza ambos repositorios con fast-forward; si no se puede (cambios
# locales o sin red), continua con la copia actual sin bloquear el editor.
$ErrorActionPreference = "Continue"
$listaRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$requiredAsset = "app\src\main\assets\resolver_catalog.json"

function Test-VibeRepository([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
    return (Test-Path -LiteralPath (Join-Path $Path "gradlew.bat")) -and
        (Test-Path -LiteralPath (Join-Path $Path $requiredAsset))
}

function Update-Repository([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path) -or
        -not (Test-Path -LiteralPath (Join-Path $Path ".git"))) { return }
    try {
        Write-Host "Buscando la ultima version en $Path ..." -ForegroundColor Cyan
        & git -C $Path pull --ff-only --quiet
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "No se pudo actualizar $Path (cambios locales o sin conexion); se usa la copia actual."
        }
    } catch {
        Write-Warning "No se pudo actualizar $Path; se usa la copia actual."
    }
}

Update-Repository $listaRoot

$resolvedVibe = $null
if (Test-VibeRepository $VibeM3UPath) {
    $resolvedVibe = (Resolve-Path -LiteralPath $VibeM3UPath).Path
} else {
    $candidates = @(
        $env:VIBEM3U_PATH,
        (Join-Path $listaRoot "..\VibeM3U"),
        (Join-Path $listaRoot "..\vibe-publish-clean"),
        (Join-Path $listaRoot "..\vibem3u")
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    $resolvedVibe = $candidates | Where-Object { Test-VibeRepository $_ } | Select-Object -First 1
}
if ($resolvedVibe) { Update-Repository $resolvedVibe }

$startScript = Join-Path $PSScriptRoot "Start-CatalogEditor.ps1"
if ($resolvedVibe) {
    & $startScript -VibeM3UPath $resolvedVibe
} else {
    & $startScript
}
