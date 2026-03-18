@echo off
TITLE SENTINEL PRO - DEMARRAGE DIRECT
setlocal enabledelayedexpansion

:: Forcer le dossier de travail
cd /d "%~dp0"
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

echo ══════════════════════════════════════════════════════════
echo DEMARRAGE DIRECT - SENTINEL PRO
echo ══════════════════════════════════════════════════════════
echo.

:: 1. Verification rapide
echo [1/2] Verification Python...
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [!] Erreur : Python introuvable.
    pause
    exit /b
)

:: 2. Lancement du Moteur (Bloquant)
echo [2/2] Lancement du Moteur...
echo (Le Dashboard Streamlit sera lance en arriere-plan)
echo.

:: Lancer le War Room (Next-Gen Dash) en arriere-plan
start "SENTINEL WAR-ROOM" /D "%~dp0" cmd /c "python interface\war_room.py"

:: Lancer le moteur ici-meme (si ca crash, on le verra)
python main.py

echo.
echo ══════════════════════════════════════════════════════════
echo LE MOTEUR S'EST ARRETE
echo ══════════════════════════════════════════════════════════
pause
