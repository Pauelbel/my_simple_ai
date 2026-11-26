@echo off
setlocal
cd /d "%~dp0apps\desktop"

where npm >nul 2>nul || (
    echo Node.js 22 is required for development.
    exit /b 1
)
where cargo >nul 2>nul || (
    echo Rust is required for Tauri development.
    exit /b 1
)

if not exist "node_modules" (
    if exist "package-lock.json" (call npm ci) else (call npm install)
)
if errorlevel 1 exit /b 1
call npm run tauri dev
