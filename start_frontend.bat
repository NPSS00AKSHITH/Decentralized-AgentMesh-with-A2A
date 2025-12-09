@echo off
echo ============================================================
echo  DDMS Frontend - React Control Center
echo ============================================================
echo.
echo Starting React development server on http://localhost:3000
echo.
echo Make sure to run start_a2a_servers.bat first for agent communication!
echo.

cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo Installing dependencies...
    npm install
)

npm run dev
