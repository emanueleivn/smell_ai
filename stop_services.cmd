@echo off
setlocal enabledelayedexpansion

rem ===============================
rem  CodeSmile - Stop servizi
rem ===============================

rem Vai alla root del repository (directory di questo script)
cd /d "%~dp0"
set "ROOT=%CD%"

echo [Info] Arresto servizi su porte 8000, 8001, 8002, 8003 e 3000...

call :kill_port "Gateway" 8000
call :kill_port "AI Service" 8001
call :kill_port "Static Analysis" 8002
call :kill_port "Report Service" 8003
call :kill_port "Next.js Frontend" 3000

echo.
echo [OK] Tentativo di arresto completato.
exit /b 0

:kill_port
set "NAME=%~1"
set "PORT=%~2"
set "FOUND=0"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT%" ^| findstr LISTENING') do (
  set "PID=%%P"
  set FOUND=1
  echo [Info] Arresto !NAME! su porta !PORT! PID=!PID!
  taskkill /F /PID !PID! >nul 2>&1
  if errorlevel 1 (
    echo [Warn] Impossibile terminare PID !PID! - potrebbe essere gia' chiuso.
  ) else (
    echo [OK] Terminato PID !PID! per !NAME!.
  )
)
if "!FOUND!"=="0" (
  echo [Info] Nessun processo in ascolto sulla porta !PORT! per !NAME!.
)
exit /b 0
