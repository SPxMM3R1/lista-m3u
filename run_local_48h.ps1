[CmdletBinding()]
param(
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$taskName = 'Lista M3U - actualizador local 48h'
$githubRepository = 'SPxMM3R1/lista-m3u'
$githubWorkflow = 'update-m3u.yml'
$logDirectory = Join-Path $projectRoot '.local-run'
$logPath = Join-Path $logDirectory 'latest.log'
$windowsPowerShell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$registrationPath = Join-Path $projectRoot 'register_local_48h_task.ps1'

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

function Invoke-LoggedNative {
    param(
        [string]$Executable,
        [string[]]$Arguments,
        [string]$Description
    )

    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $output = @(& $Executable @Arguments 2>&1)
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousErrorActionPreference
    foreach ($entry in $output) {
        Add-Content -LiteralPath $logPath -Value ([string]$entry)
    }
    if ($exitCode -ne 0) {
        throw "$Description fallo con codigo $exitCode"
    }
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

function Register-NextLocalRun {
    Invoke-LoggedNative `
        -Executable $windowsPowerShell `
        -Arguments @(
            '-NoProfile',
            '-ExecutionPolicy',
            'Bypass',
            '-File',
            $registrationPath
        ) `
        -Description 'La reprogramacion local dinamica'
}

$today = (Get-Date).Date
if ($today -ge [datetime]'2026-09-02') {
    try {
        $ghCommand = Get-Command gh -ErrorAction SilentlyContinue
        $ghCandidates = @(
            $(if ($ghCommand) { $ghCommand.Source }),
            (Join-Path $env:ProgramFiles 'GitHub CLI\gh.exe'),
            (Join-Path $env:LOCALAPPDATA 'Programs\GitHub CLI\gh.exe')
        )
        $ghPath = Resolve-Executable -Candidates $ghCandidates -Label 'GitHub CLI'
        Invoke-LoggedNative `
            -Executable $ghPath `
            -Arguments @('workflow', 'enable', $githubWorkflow, '--repo', $githubRepository) `
            -Description 'La reactivacion de GitHub Actions'
        Add-Content -LiteralPath $logPath -Value "[$(Get-Date -Format o)] GitHub Actions reactivado: $githubWorkflow."
        Disable-ScheduledTask -TaskName $taskName -ErrorAction Stop | Out-Null
        Add-Content -LiteralPath $logPath -Value "[$(Get-Date -Format o)] Tarea local deshabilitada tras reactivar GitHub."
        exit 0
    } catch {
        $errorMessage = $_.Exception.Message
        if (-not $errorMessage) { $errorMessage = $_.ToString() }
        Add-Content -LiteralPath $logPath -Value "[$(Get-Date -Format o)] ERROR al reactivar GitHub o deshabilitar la tarea: $errorMessage"
        Write-Error -Message $errorMessage
        exit 1
    }
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

    Invoke-LoggedNative -Executable $gitPath -Arguments @('fetch', 'origin', 'main') -Description 'git fetch'

    $countsText = ((@(& $gitPath rev-list --left-right --count HEAD...origin/main) -join " ")).Trim()
    $counts = ($countsText -split '\s+')
    $ahead = [int]$counts[0]
    $behind = [int]$counts[1]
    if ($behind -gt 0 -and $ahead -eq 0) {
        Invoke-LoggedNative -Executable $gitPath -Arguments @('merge', '--ff-only', 'origin/main') -Description 'La sincronizacion fast-forward'
    } elseif ($ahead -gt 0 -and $behind -eq 0) {
        Invoke-LoggedNative -Executable $gitPath -Arguments @('push', 'origin', 'HEAD:main') -Description 'El push pendiente'
        Register-NextLocalRun
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
    Invoke-LoggedNative -Executable $pythonPath -Arguments $coordinatorArguments -Description 'El coordinador/actualizador'

    $changes = ((@(& $gitPath status --porcelain --untracked-files=no) -join "`n")).Trim()
    if (-not $changes) {
        Add-Content -LiteralPath $logPath -Value 'No habia una ventana dinamica vencida.'
        Register-NextLocalRun
        exit 0
    }

    $changedPaths = @(& $gitPath diff --name-only)
    $allowedPaths = @('m3u.m3u', 'epg.xml', 'run-state.json')
    $unexpected = @($changedPaths | Where-Object { $_ -and ($_ -notin $allowedPaths) })
    if ($unexpected.Count -gt 0) {
        throw "El actualizador modifico rutas no autorizadas: $($unexpected -join ', ')"
    }

    Invoke-LoggedNative -Executable $gitPath -Arguments @('add', '--', 'm3u.m3u', 'epg.xml', 'run-state.json') -Description 'git add'
    $staged = @(& $gitPath diff --cached --name-only)
    $unexpectedStaged = @($staged | Where-Object { $_ -and ($_ -notin $allowedPaths) })
    if ($unexpectedStaged.Count -gt 0) {
        throw "El staging contiene rutas no autorizadas: $($unexpectedStaged -join ', ')"
    }
    Invoke-LoggedNative -Executable $gitPath -Arguments @('config', 'user.name', 'Actualizador M3U') -Description 'git config user.name'
    Invoke-LoggedNative -Executable $gitPath -Arguments @('config', 'user.email', 'm3u-bot@users.noreply.github.com') -Description 'git config user.email'
    Invoke-LoggedNative -Executable $gitPath -Arguments @('commit', '-m', 'Actualiza M3U y EPG automaticamente [skip ci]') -Description 'git commit'
    Invoke-LoggedNative -Executable $gitPath -Arguments @('push', 'origin', 'HEAD:main') -Description 'git push'

    $rawBase = 'https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main'
    Invoke-LoggedNative -Executable $pythonPath -Arguments @((Join-Path $projectRoot 'update_m3u.py'), '--verify-published', "$rawBase/m3u.m3u") -Description 'La verificacion Raw de M3U'
    Invoke-LoggedNative -Executable $pythonPath -Arguments @((Join-Path $projectRoot 'update_m3u.py'), '--verify-epg-published', "$rawBase/epg.xml") -Description 'La verificacion Raw de EPG'
    Add-Content -LiteralPath $logPath -Value "[$(Get-Date -Format o)] Publicacion local verificada."
    Register-NextLocalRun
} catch {
    $errorMessage = $_.Exception.Message
    if (-not $errorMessage) { $errorMessage = $_.ToString() }
    Add-Content -LiteralPath $logPath -Value "[$(Get-Date -Format o)] ERROR: $errorMessage"
    try {
        Register-NextLocalRun
        Add-Content -LiteralPath $logPath -Value "[$(Get-Date -Format o)] Reintento dinamico programado."
    } catch {
        $rescheduleError = $_.Exception.Message
        if (-not $rescheduleError) { $rescheduleError = $_.ToString() }
        Add-Content -LiteralPath $logPath -Value "[$(Get-Date -Format o)] ERROR al programar reintento: $rescheduleError"
    }
    Write-Error -Message $errorMessage
    exit 1
} finally {
    Pop-Location
}
