@echo off
SETLOCAL EnableDelayedExpansion

:: --- CONFIGURATION ---
SET "PYTHON_EXE=python"
SET "VENV_DIR=venv"
SET "ROOT_DIR=%~dp0"

cd /d "%ROOT_DIR%"

:: --- VÉRIFICATION VENV ---
IF EXIST "%VENV_DIR%\Scripts\activate.bat" (
    echo [INFO] Activation de l'environnement virtuel...
    call "%VENV_DIR%\Scripts\activate.bat"
) ELSE (
    echo [ATTENTION] Environnement virtuel '%VENV_DIR%' non trouve. Utilisation du Python systeme.
)

:MENU
cls
echo ============================================================
echo   ICT SENTINEL PRO - GESTIONNAIRE DE LANCEMENT
echo ============================================================
echo.
echo   1. Lancer le BOT (Trading Autonome)
echo   2. Lancer l'INTERFACE (Analyse ICT ^& Monitor)
echo   3. Verifier la connexion MetaTrader 5
echo   4. Quitter
echo.
set /p choice="Votre choix [1-4] : "

IF "%choice%"=="1" GOTO RUN_BOT
IF "%choice%"=="2" GOTO RUN_UI
IF "%choice%"=="3" GOTO CHECK_MT5
IF "%choice%"=="4" GOTO END
GOTO MENU

:RUN_BOT
echo [Lancement] ICT Trading Bot...
"%PYTHON_EXE%" bot_runner.py
pause
GOTO MENU

:RUN_UI
echo [Lancement] Interface Monitoring (Streamlit)...
"%PYTHON_EXE%" -m streamlit run main.py
pause
GOTO MENU

:CHECK_MT5
echo [Verification] Connexion MetaTrader 5...
if exist "scripts\check_mt5_data.py" (
    "%PYTHON_EXE%" scripts\check_mt5_data.py
) else (
    echo Script 'scripts/check_mt5_data.py' introuvable.
)
pause
GOTO MENU

:END
exit
