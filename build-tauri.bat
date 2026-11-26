@echo off
setlocal
cd /d "%~dp0apps\desktop"

call npm ci
if errorlevel 1 exit /b 1
call npm run check
if errorlevel 1 exit /b 1
call npm run tauri -- build --target x86_64-pc-windows-msvc -- --locked
