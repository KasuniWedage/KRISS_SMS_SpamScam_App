@echo off
REM ============================================================
REM  KRISS Database Backup Windows Task Scheduler Batch Setup
REM ============================================================

set PROJECT_ROOT=D:\KRISS_SMS_SpamScam_App_Updated
set PYTHON_EXE=%PROJECT_ROOT%\backend\.venv\Scripts\python.exe

if not exist "%PYTHON_EXE%" (
    set PYTHON_EXE=python.exe
)

set SCRIPT_PATH=%PROJECT_ROOT%\backend\scripts\database_backup.py
set TASK_NAME=KRISS Daily Database Backup

echo [1/3] Registering Task in Windows Task Scheduler (Daily at 02:00 AM)...
schtasks /Create /SC DAILY /ST 02:00 /TN "%TASK_NAME%" /TR "\"%PYTHON_EXE%\" \"%SCRIPT_PATH%\" --verify" /F

echo.
echo [2/3] Querying Task Configuration...
schtasks /Query /TN "%TASK_NAME%" /V /FO LIST

echo.
echo [3/3] Executing immediate test backup run...
"%PYTHON_EXE%" "%SCRIPT_PATH%" --verify

echo.
echo [SUCCESS] Backup scheduler registered and verified successfully.
pause
