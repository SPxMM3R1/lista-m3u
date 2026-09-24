param(
    [string]$VibeM3UPath
)

$ErrorActionPreference = "Stop"
$listaRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$requiredAsset = "app\src\main\assets\resolver_catalog.json"

function Test-VibeRepository([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
    return (Test-Path -LiteralPath (Join-Path $Path "gradlew.bat")) -and
        (Test-Path -LiteralPath (Join-Path $Path $requiredAsset))
}

if ([string]::IsNullOrWhiteSpace($VibeM3UPath)) {
    $candidates = @(
        $env:VIBEM3U_PATH,
        (Join-Path $listaRoot "..\VibeM3U"),
        (Join-Path $listaRoot "..\vibe-publish-clean"),
        (Join-Path $listaRoot "..\vibem3u")
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    $VibeM3UPath = $candidates | Where-Object { Test-VibeRepository $_ } | Select-Object -First 1
}

if (-not (Test-VibeRepository $VibeM3UPath)) {
    $VibeM3UPath = Read-Host "Ruta a la carpeta local de VibeM3U"
}
if (-not (Test-VibeRepository $VibeM3UPath)) {
    throw "No encuentro gradlew.bat y $requiredAsset en la ruta de VibeM3U indicada."
}
$vibeRoot = (Resolve-Path -LiteralPath $VibeM3UPath).Path

$pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonLauncher -and -not $python) {
    throw "Se necesita Python 3 instalado para generar los datos locales del editor."
}

$localSite = Join-Path ([System.IO.Path]::GetTempPath()) ("lista-m3u-editor-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $localSite | Out-Null
$buildScript = Join-Path $listaRoot "scripts\build_site_data.py"
try {
    if ($pythonLauncher) {
        & $pythonLauncher.Source -3 $buildScript --output $localSite
    } else {
        & $python.Source $buildScript --output $localSite
    }
    if ($LASTEXITCODE -ne 0) { throw "Falló la preparación local del catálogo. Revisa la salida del runner." }

    $probe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $probe.Start()
    $port = $probe.LocalEndpoint.Port
    $probe.Stop()

    $gradle = Join-Path $vibeRoot "gradlew.bat"
    $gradleArgs = @(
        "--no-daemon",
        "-p", $vibeRoot,
        ":local-catalog:installDist"
    )

    Write-Host "Editor local preparado. No se publica ni modifica el repositorio al iniciarlo." -ForegroundColor Green
    Write-Host "Las listas M3U se leen desde: $listaRoot"
    Write-Host "VibeM3U y sus resolutores se leen desde: $vibeRoot"
    Write-Host "Deja esta ventana abierta; Ctrl+C detiene el servicio local."
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        Write-Warning "GitHub CLI (gh) no está instalado. Podrás explorar y probar canales, pero no conectar ni publicar desde GitHub hasta instalarlo."
    }

    & $gradle @gradleArgs
    if ($LASTEXITCODE -ne 0) { throw "No se pudo preparar el auxiliar local de VibeM3U." }

    $catalogRunner = Join-Path $vibeRoot "local-catalog\build\install\local-catalog\bin\local-catalog.bat"
    if (-not (Test-Path -LiteralPath $catalogRunner)) {
        throw "Gradle terminó sin generar el lanzador local esperado: $catalogRunner"
    }
    & $catalogRunner `
        --web-root $localSite `
        --lista-root $listaRoot `
        --vibe-root $vibeRoot `
        --port $port
    if ($LASTEXITCODE -ne 0) { throw "No se pudo iniciar el auxiliar local de VibeM3U." }
} finally {
    if (Test-Path -LiteralPath $localSite) {
        $siteDirectory = Get-Item -LiteralPath $localSite
        $tempRoot = (Resolve-Path -LiteralPath ([System.IO.Path]::GetTempPath())).Path.TrimEnd('\', '/')
        $isDedicatedTempFolder = $siteDirectory.Parent.FullName.TrimEnd('\', '/').Equals($tempRoot, [System.StringComparison]::OrdinalIgnoreCase)
        $isGeneratedSite = $siteDirectory.Name -match '^lista-m3u-editor-[0-9a-f]{32}$'
        if ($isDedicatedTempFolder -and $isGeneratedSite) {
            Remove-Item -LiteralPath $siteDirectory.FullName -Recurse -Force
        }
    }
}
