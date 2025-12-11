@echo off
setlocal enabledelayedexpansion

rem ===============================
rem  CodeSmile - Avvio servizi
rem ===============================

rem Vai alla root del repository (directory di questo script)
cd /d "%~dp0"
set "ROOT=%CD%"

rem Attiva il virtualenv se esiste
if exist "%ROOT%\venv\Scripts\activate.bat" (
  call "%ROOT%\venv\Scripts\activate.bat"
  echo [Info] Virtualenv attivato.
) else (
  echo [Avviso] Virtualenv non trovato in %ROOT%\venv. Uso Python di sistema.
)

rem Rende importabile il pacchetto "webapp.*" negli uvicorn
set "PYTHONPATH=%ROOT%"

rem Verifica uvicorn, installa se assente (minimo indispensabile)
where uvicorn >nul 2>&1
if errorlevel 1 (
  echo [Info] uvicorn non trovato. Installo uvicorn e fastapi...
  pip install uvicorn fastapi >nul
)

rem Verifica npm
where npm >nul 2>&1
if errorlevel 1 (
  echo [Errore] npm non trovato nel PATH. Installa Node.js prima di continuare: https://nodejs.org/
  goto :after_start
)

rem Avvia i servizi FastAPI in background (stessa finestra)
start "Gateway (8000)" /B /D "%ROOT%\webapp\gateway" uvicorn main:app --host 0.0.0.0 --port 8000
start "AI Service (8001)" /B /D "%ROOT%" uvicorn webapp.services.aiservice.app.main:app --host 0.0.0.0 --port 8001
start "Static Analysis (8002)" /B /D "%ROOT%" uvicorn webapp.services.staticanalysis.app.main:app --host 0.0.0.0 --port 8002
start "Report (8003)" /B /D "%ROOT%" uvicorn webapp.services.report.app.main:app --host 0.0.0.0 --port 8003

rem Piccola pausa per permettere l'avvio dei servizi
ping -n 3 127.0.0.1 >nul

rem Build e start della webapp Next.js
pushd "%ROOT%\webapp"
if exist "package-lock.json" (
  call npm ci
) else (
  call npm install
)
call npm run build
start "Next.js Frontend (3000)" /B /D "%ROOT%\webapp" npm run start
popd

:after_start
echo.
echo [OK] Servizi avviati:
echo   - Gateway:           http://localhost:8000
echo   - AI Service:        http://localhost:8001
echo   - Static Analysis:   http://localhost:8002
echo   - Report Service:    http://localhost:8003
echo   - Frontend Next.js:  http://localhost:3000

endlocal
exit /b 0

