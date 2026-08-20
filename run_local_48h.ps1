[CmdletBinding()]
param(
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$taskName = 'Lista M3U - actualizador local 48h'
$logDirectory = Join-Path $projectRoot '.local-run'
$logPath = Join-Path $logDirectory 'latest.log'

New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null

function Resolve-Executable {
    param(
        [string[]]$Candidates,
        [string]$Label
    )

    foreach ($candidate in $Candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return $candidate
        }
    }
    throw "No se encontro $Label compatible."
}

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
$gitCommand = Get-Command git -ErrorAction SilentlyContinue
$pythonCandidates = @(
    (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'),
    $(if ($pythonCommand) { $pythonCommand.Source }),
    (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe')
)
$gitCandidates = @(
    $(if ($gitCommand) { $gitCommand.Source }),
    (Join-Path $env:ProgramFiles 'Git\cmd\git.exe'),
    (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe')
)
$pythonPath = Resolve-Executable -Candidates $pythonCandidates -Label 'Python'
$gitPath = Resolve-Executable -Candidates $gitCandidates -Label 'Git'

$today = (Get-Date).Date
if ($today -ge [datetime]'2026-09-02') {
    try {
        Disable-ScheduledTask -TaskName $taskName -ErrorAction Stop | Out-Null
    } catch {
        # El coordinador Python tambien bloquea la ventana local; no se fuerza
        # un error si Windows ya deshabilito o elimino la tarea.
    }
    Add-Content -LiteralPath $logPath -Value "[$(Get-Date -Format o)] Ventana local finalizada; tarea deshabilitada."
    exit 0
}

Push-Location $projectRoot
try {
    "[$(Get-Date -Format o)] Inicio del ejecutor local" | Set-Content -LiteralPath $logPath -Encoding UTF8

    $branch = ((@(& $gitPath rev-parse --abbrev-ref HEAD) -join "`n")).Trim()
    if ($branch -ne 'main') {
        throw "El ejecutor local requiere la rama main; rama actual: $branch"
    }

    $trackedChanges = ((@(& $gitPath status --porcelain --untracked-files=no) -join "`n")).Trim()
    if ($trackedChanges) {
        throw "Hay cambios tracked antes de iniciar; no se sobrescriben: $trackedChanges"
    }

    & $gitPath fetch origin main 2>&1 | Tee-Object -FilePath $logPath -Append
    if ($LASTEXITCODE -ne 0) { throw 'git fetch fallo' }

    $countsText = ((@(& $gitPath rev-list --left-right --count HEAD...origin/main) -join " ")).Trim()
    $counts = ($countsText -split '\s+')
    $ahead = [int]$counts[0]
    $behind = [int]$counts[1]
    if ($behind -gt 0 -and $ahead -eq 0) {
        & $gitPath merge --ff-only origin/main 2>&1 | Tee-Object -FilePath $logPath -Append
        if ($LASTEXITCODE -ne 0) { throw 'La sincronizacion fast-forward fallo' }
    } elseif ($ahead -gt 0 -and $behind -eq 0) {
        & $gitPath push origin HEAD:main 2>&1 | Tee-Object -FilePath $logPath -Append
        if ($LASTEXITCODE -ne 0) { throw 'Habia una publicacion local pendiente y el push fallo' }
        exit 0
    } elseif ($ahead -gt 0 -and $behind -gt 0) {
        throw 'La rama local y origin/main divergieron; se requiere revision manual'
    }

    $coordinatorArguments = @(
        (Join-Path $projectRoot 'run_m3u_48h.py'),
        '--executor',
        'local'
    )
    if ($Force) { $coordinatorArguments += '--force' }
    & $pythonPath @coordinatorArguments 2>&1 | Tee-Object -FilePath $logPath -Append
    if ($LASTEXITCODE -ne 0) { throw 'El coordinador/actualizador fallo' }

    $changes = ((@(& $gitPath status --porcelain --untracked-files=no) -join "`n")).Trim()
    if (-not $changes) {
        Add-Content -LiteralPath $logPath -Value 'No habia una ventana de 48 horas vencida.'
        exit 0
    }

    $changedPaths = @(& $gitPath diff --name-only)
    $allowedPaths = @('m3u.m3u', 'epg.xml', 'run-state.json')
    $unexpected = @($changedPaths | Where-Object { $_ -and ($_ -notin $allowedPaths) })
    if ($unexpected.Count -gt 0) {
        throw "El actualizador modifico rutas no autorizadas: $($unexpected -join ', ')"
    }

    & $gitPath add -- m3u.m3u epg.xml run-state.json 2>&1 | Tee-Object -FilePath $logPath -Append
    if ($LASTEXITCODE -ne 0) { throw 'git add fallo' }
    $staged = @(& $gitPath diff --cached --name-only)
    $unexpectedStaged = @($staged | Where-Object { $_ -and ($_ -notin $allowedPaths) })
    if ($unexpectedStaged.Count -gt 0) {
        throw "El staging contiene rutas no autorizadas: $($unexpectedStaged -join ', ')"
    }
    & $gitPath config user.name 'Actualizador M3U'
    & $gitPath config user.email 'm3u-bot@users.noreply.github.com'
    & $gitPath commit -m 'Actualiza M3U y EPG automaticamente [skip ci]' 2>&1 | Tee-Object -FilePath $logPath -Append
    if ($LASTEXITCODE -ne 0) { throw 'git commit fallo' }
    & $gitPath push origin HEAD:main 2>&1 | Tee-Object -FilePath $logPath -Append
    if ($LASTEXITCODE -ne 0) { throw 'git push fallo; el commit local queda preparado para reintento' }

    $rawBase = 'https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main'
    & $pythonPath (Join-Path $projectRoot 'update_m3u.py') '--verify-published' "$rawBase/m3u.m3u" 2>&1 | Tee-Object -FilePath $logPath -Append
    if ($LASTEXITCODE -ne 0) { throw 'La verificacion Raw de M3U fallo' }
    & $pythonPath (Join-Path $projectRoot 'update_m3u.py') '--verify-epg-published' "$rawBase/epg.xml" 2>&1 | Tee-Object -FilePath $logPath -Append
    if ($LASTEXITCODE -ne 0) { throw 'La verificacion Raw de EPG fallo' }
    Add-Content -LiteralPath $logPath -Value "[$(Get-Date -Format o)] Publicacion local verificada."
} catch {
    $errorMessage = $_.Exception.Message
    if (-not $errorMessage) { $errorMessage = $_.ToString() }
    Add-Content -LiteralPath $logPath -Value "[$(Get-Date -Format o)] ERROR: $errorMessage"
    Write-Error -Message $errorMessage
    exit 1
} finally {
    Pop-Location
}
