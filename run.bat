@echo off
setlocal enabledelayedexpansion
title SOURCERY Launcher

:menu
cls
echo.
echo  [1] Install dependencies
echo  [2] Start dev server
echo  [3] Run CLI query (stub)
echo  [4] Run tests
echo  [5] Open http://localhost:3000
echo  [Q] Quit
echo.
set /p choice="Select: "

if "!choice!"=="1" goto install
if "!choice!"=="2" goto dev
if "!choice!"=="3" goto cli
if "!choice!"=="4" goto test
if "!choice!"=="5" goto open
if /i "!choice!"=="Q" exit

echo Invalid choice & timeout /t 1 >nul & goto menu

:install
echo Installing...
call npm install
call uv sync --all-extras
echo Done & timeout /t 1 >nul & goto menu

:dev
echo Killing existing processes on ports 3000 and 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
echo Cleaning corrupted Next.js cache...
if exist .next rmdir /s /q .next >nul 2>&1
echo Starting Python API on :8000 and Next.js on :3000...
start "SOURCERY-API" cmd /k "uv run python scripts\dev_server.py"
start "SOURCERY-WEB" cmd /k "npm run dev"
echo Waiting for frontend to compile...
timeout /t 3 >nul
start http://localhost:3000
pause
goto menu

:cli
set /p query="Query: "
if "!query!"=="" goto cli
echo Running...
call uv run sourcery "!query!" --out outputs\cli_run --provider stub
echo Done & timeout /t 2 >nul & goto menu

:test
echo Running tests...
call uv run pytest -q
pause
goto menu

:open
start http://localhost:3000
goto menu