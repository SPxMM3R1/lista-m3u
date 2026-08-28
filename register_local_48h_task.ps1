[CmdletBinding()]
param(
    [switch]$Unregister
)

$ErrorActionPreference = 'Stop'
$taskName = 'Lista M3U - actualizador local 48h'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runnerPath = Join-Path $projectRoot 'run_local_48h.ps1'
$statePath = Join-Path $projectRoot 'run-state.json'
$windowsPowerShell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'

if ($Unregister) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "Tarea retirada: $taskName"
    exit 0
}

$action = New-ScheduledTaskAction `
    -Execute $windowsPowerShell `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runnerPath`""
$now = Get-Date
$firstRun = $now.AddMinutes(15)
if (Test-Path -LiteralPath $statePath -PathType Leaf) {
    try {
        $state = Get-Content -Raw -LiteralPath $statePath | ConvertFrom-Json
        $scheduledNext = $null
        if ($state.next_scheduled_at) {
            $scheduledNext = [DateTimeOffset]::Parse($state.next_scheduled_at).ToLocalTime().DateTime
        } elseif ($state.last_published_at) {
            $scheduledNext = [DateTimeOffset]::Parse($state.last_published_at).ToLocalTime().DateTime.AddHours(12)
        }
        if ($scheduledNext -and $scheduledNext -gt $now) {
            $firstRun = $scheduledNext
        }
    } catch {
        Write-Warning "No se pudo leer la proxima ventana desde run-state.json; se usara un reintento en 15 minutos."
    }
}
$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At $firstRun
$resumeTrigger = New-ScheduledTaskTrigger `
    -Once `
    -At ([datetime]'2026-09-02T03:05:00')
$triggers = @($trigger, $resumeTrigger)
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $triggers `
    -Settings $settings `
    -Principal $principal `
    -Description 'Ejecuta Lista M3U en la proxima ventana dinamica de la guia, con limite de 12 horas, y reactiva GitHub Actions el 2 de septiembre de 2026.' `
    -Force | Out-Null

Write-Output "Tarea registrada: $taskName"
Write-Output "Primera ejecucion programada: $($firstRun.ToString('yyyy-MM-dd HH:mm:ss'))"
Write-Output 'La tarea usa una ejecucion unica y se vuelve a programar segun el vencimiento real de la guia, con limite de 12 horas y minimo de 6 horas.'
Write-Output 'Tambien contiene un disparador puntual para reactivar GitHub el 2026-09-02 03:05.'
