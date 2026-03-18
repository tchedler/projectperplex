@echo off
TITLE SENTINEL PRO KB5
setlocal enabledelayedexpansion
color 0A

set "PY311=C:\Users\djerm\AppData\Local\Programs\Python\Python311\python.exe"
set "STREAMLIT311=C:\Users\djerm\AppData\Local\Programs\Python\Python311\Scripts\streamlit.exe"
set "PROTO=PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python"

cd /D "%~dp0"

echo ========================================================
echo   SENTINEL PRO KB5 — LANCEMENT
echo ========================================================
echo.

echo [1/2] Lancement du Cerveau KB5...
start "SENTINEL KB5 - Cerveau" /D "%~dp0" cmd /k "set %PROTO%&& set PYTHONPATH=%~dp0&& "%PY311%" main.py"

echo Attente 6 secondes...
timeout /t 6 >nul

echo [2/2] Lancement Interface Streamlit port 8502...
start "SENTINEL KB5 - Interface" /D "%~dp0" cmd /k "set %PROTO%&& set PYTHONPATH=%~dp0&& "%STREAMLIT311%" run main_streamlit.py --server.port 8502"

echo Ouverture navigateur dans 4 secondes...
timeout /t 4 >nul
start http://localhost:8502

echo.
echo ========================================================
echo   Interface : http://localhost:8502
echo   Pour arreter : fermez les deux fenetres noires
echo ========================================================
pause
