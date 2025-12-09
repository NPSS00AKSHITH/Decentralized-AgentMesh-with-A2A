@echo off
setlocal enabledelayedexpansion

:: ============================================================
:: A2A Server Launcher - Runs custom main.py A2A servers
:: ============================================================
:: These servers expose the A2A protocol endpoint at root /
:: Run this ALONGSIDE start_agents.bat (which runs adk web for UI)

:: 1. Set Project Root
cd /d "%~dp0"
set "PROJECT_ROOT=%~dp0"
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
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo Run: python -m venv .venv && .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b
)

:: 4. Start A2A Servers using custom main.py (ports 9001-9009)
echo.
echo ============================================================
echo  Starting A2A Protocol Servers (custom main.py)
echo  These expose A2A endpoints at / for inter-agent communication
echo ============================================================
echo.

:: Set PORT env var for each agent before starting
start "A2A: Human Intake" cmd /k "set PYTHONPATH=%PROJECT_ROOT% && set PORT=9001 && cd agents\human_intake_folder && "%PROJECT_ROOT%\.venv\Scripts\python" -m human_intake.main"
start "A2A: Dispatch" cmd /k "set PYTHONPATH=%PROJECT_ROOT% && set PORT=9002 && cd agents\dispatch_folder && "%PROJECT_ROOT%\.venv\Scripts\python" -m dispatch.main"
start "A2A: Fire Chief" cmd /k "set PYTHONPATH=%PROJECT_ROOT% && set PORT=9003 && cd agents\fire_chief_folder && "%PROJECT_ROOT%\.venv\Scripts\python" -m fire_chief.main"
start "A2A: Civic Alert" cmd /k "set PYTHONPATH=%PROJECT_ROOT% && set PORT=9004 && cd agents\civic_alert_folder && "%PROJECT_ROOT%\.venv\Scripts\python" -m civic_alert.main"
start "A2A: Medical" cmd /k "set PYTHONPATH=%PROJECT_ROOT% && set PORT=9005 && cd agents\medical_folder && "%PROJECT_ROOT%\.venv\Scripts\python" -m medical.main"
start "A2A: Police Chief" cmd /k "set PYTHONPATH=%PROJECT_ROOT% && set PORT=9006 && cd agents\police_chief_folder && "%PROJECT_ROOT%\.venv\Scripts\python" -m police_chief.main"
start "A2A: Utility" cmd /k "set PYTHONPATH=%PROJECT_ROOT% && set PORT=9007 && cd agents\utility_folder && "%PROJECT_ROOT%\.venv\Scripts\python" -m utility.main"
start "A2A: IoT Sensor" cmd /k "set PYTHONPATH=%PROJECT_ROOT% && set PORT=9008 && cd agents\iot_sensor_folder && "%PROJECT_ROOT%\.venv\Scripts\python" -m iot_sensor.main"
start "A2A: Camera" cmd /k "set PYTHONPATH=%PROJECT_ROOT% && set PORT=9009 && cd agents\camera_folder && "%PROJECT_ROOT%\.venv\Scripts\python" -m camera.main"

echo.
echo All A2A servers initialized on ports 9001-9009.
echo.
echo Port Mapping:
echo   Human Intake : 9001 (A2A) / 8001 (Web UI)
echo   Dispatch     : 9002 (A2A) / 8002 (Web UI)
echo   Fire Chief   : 9003 (A2A) / 8003 (Web UI)
echo   Civic Alert  : 9004 (A2A) / 8004 (Web UI)
echo   Medical      : 9005 (A2A) / 8005 (Web UI)
echo   Police Chief : 9006 (A2A) / 8006 (Web UI)
echo   Utility      : 9007 (A2A) / 8007 (Web UI)
echo   IoT Sensor   : 9008 (A2A) / 8008 (Web UI)
echo   Camera       : 9009 (A2A) / 8009 (Web UI)
echo.
