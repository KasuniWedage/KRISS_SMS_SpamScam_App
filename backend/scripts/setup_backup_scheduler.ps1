<#
.SYNOPSIS
    Configures Windows Task Scheduler for Automated Daily KRISS Database Backups.
.DESCRIPTION
    Registers a daily scheduled task at 02:00 AM running database_backup.py,
    logs results to backend/backups/backup_history.jsonl, and queries status.
#>

$ErrorActionPreference = "Stop"

$ProjectRoot = "D:\KRISS_SMS_SpamScam_App_Updated"
$PythonExe = "$ProjectRoot\backend\.venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = (Get-Command python.exe).Source
}

$ScriptPath = "$ProjectRoot\backend\scripts\database_backup.py"
$TaskName = "KRISS Daily Database Backup"
$TaskTime = "02:00"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " KRISS Database Backup Task Scheduler Configuration" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Project Root: $ProjectRoot"
Write-Host "Python:       $PythonExe"
Write-Host "Script:       $ScriptPath"
Write-Host "Schedule:     Daily at $TaskTime"

# Register Task
$Action = "-Command `"$PythonExe $ScriptPath --verify`""
$SchtasksCmd = "schtasks /Create /SC DAILY /ST $TaskTime /TN `"$TaskName`" /TR `"powershell.exe $Action`" /F"

Write-Host "`n[1/3] Registering Task in Windows Task Scheduler..." -ForegroundColor Yellow
cmd.exe /c $SchtasksCmd

Write-Host "`n[2/3] Querying Task Configuration..." -ForegroundColor Yellow
schtasks /Query /TN "$TaskName" /V /FO LIST

Write-Host "`n[3/3] Executing immediate verification run..." -ForegroundColor Yellow
& $PythonExe $ScriptPath --verify

Write-Host "`n[SUCCESS] Daily backup task scheduler configured successfully!" -ForegroundColor Green
