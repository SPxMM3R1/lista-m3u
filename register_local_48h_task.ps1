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
$firstRun = (Get-Date).AddMinutes(1)
if (Test-Path -LiteralPath $statePath -PathType Leaf) {
    $state = Get-Content -Raw -LiteralPath $statePath | ConvertFrom-Json
    if ($state.last_published_at) {
        $scheduledNext = [DateTimeOffset]::Parse($state.last_published_at).ToLocalTime().DateTime.AddHours(48)
        if ($scheduledNext -gt (Get-Date)) {
            $firstRun = $scheduledNext
        }
    }
}
$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At $firstRun `
    -RepetitionInterval (New-TimeSpan -Hours 48) `
    -RepetitionDuration (New-TimeSpan -Days 14)
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
    -Description 'Ejecuta Lista M3U cada 48 horas durante la ventana local y reactiva GitHub Actions el 2 de septiembre de 2026.' `
    -Force | Out-Null

Write-Output "Tarea registrada: $taskName"
Write-Output "Primera ejecucion programada: $($firstRun.ToString('yyyy-MM-dd HH:mm:ss'))"
Write-Output 'La tarea se repite cada 48 horas y contiene un disparador puntual para reactivar GitHub el 2026-09-02 03:05.'
