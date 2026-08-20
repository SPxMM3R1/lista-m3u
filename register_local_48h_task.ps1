[CmdletBinding()]
param(
    [switch]$Unregister
)

$ErrorActionPreference = 'Stop'
$taskName = 'Lista M3U - actualizador local 48h'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runnerPath = Join-Path $projectRoot 'run_local_48h.ps1'
$windowsPowerShell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'

if ($Unregister) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "Tarea retirada: $taskName"
    exit 0
}

$action = New-ScheduledTaskAction `
    -Execute $windowsPowerShell `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runnerPath`""
$trigger = New-ScheduledTaskTrigger -Daily -At ([datetime]::Today.AddHours(3)) -DaysInterval 1
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
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description 'Ejecuta la validacion y publicacion de Lista M3U solo cuando vencen 48 horas; se detiene al comenzar el 2 de septiembre de 2026.' `
    -Force | Out-Null

Write-Output "Tarea registrada: $taskName"
Write-Output 'La tarea se despierta diariamente a las 03:00, pero el coordinador solo ejecuta el flujo completo cada 48 horas.'
