# Registers a Windows scheduled task that runs the collector every hour,
# starting at logon. Run from the project folder:  .\register_task.ps1

$ProjectDir = $PSScriptRoot
$Python = Join-Path $ProjectDir ".venv\Scripts\pythonw.exe"
$TaskName = "ClaudeUsageCollector"

if (-not (Test-Path $Python)) {
    Write-Error "Environnement virtuel introuvable : $Python. Lancez d'abord l'installation (voir README)."
    exit 1
}

$Action = New-ScheduledTaskAction -Execute $Python -Argument "-m claude_usage --once" -WorkingDirectory $ProjectDir
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1)
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Force | Out-Null
Write-Host "Tâche '$TaskName' enregistrée : collecte toutes les heures."
