@echo off
setlocal enabledelayedexpansion

:: 1. Set Project Root
cd /d "%~dp0"
set "PROJECT_ROOT=%~dp0"
:: IMPORTANT: Strip trailing backslash for cleaner paths
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

set "PYTHONPATH=%PROJECT_ROOT%"

:: 2. Load .env
if exist .env (
    echo Loading .env variables...
    for /f "usebackq tokens=1* delims==" %%A in (".env") do (
        if "%%A" neq "" set "%%A=%%B"
    )
) else (
    echo [WARNING] .env file not found!
)

:: 3. Check Venv
if not exist ".venv\Scripts\adk.exe" (
    echo [ERROR] Virtual environment not found.
    echo Run: python -m venv .venv && .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b
)

:: 4. Start Agents
echo Starting Agents with PYTHONPATH=%PYTHONPATH%

start "Human Intake" cmd /k "cd agents\human_intake_folder && "%PROJECT_ROOT%\.venv\Scripts\adk" web --port 8001"
start "Dispatch" cmd /k "cd agents\dispatch_folder && "%PROJECT_ROOT%\.venv\Scripts\adk" web --port 8002"
start "Fire Chief" cmd /k "cd agents\fire_chief_folder && "%PROJECT_ROOT%\.venv\Scripts\adk" web --port 8003"
start "Civic Alert" cmd /k "cd agents\civic_alert_folder && "%PROJECT_ROOT%\.venv\Scripts\adk" web --port 8004"
start "Medical" cmd /k "cd agents\medical_folder && "%PROJECT_ROOT%\.venv\Scripts\adk" web --port 8005"
start "Police Chief" cmd /k "cd agents\police_chief_folder && "%PROJECT_ROOT%\.venv\Scripts\adk" web --port 8006"
start "Utility" cmd /k "cd agents\utility_folder && "%PROJECT_ROOT%\.venv\Scripts\adk" web --port 8007"
start "IoT Sensor" cmd /k "cd agents\iot_sensor_folder && "%PROJECT_ROOT%\.venv\Scripts\adk" web --port 8008"
start "Camera" cmd /k "cd agents\camera_folder && "%PROJECT_ROOT%\.venv\Scripts\adk" web --port 8009"

echo All agents initialized.