@echo off
TITLE SENTINEL PRO KB5 — Launchpad
setlocal enabledelayedexpansion

:: ══════════════════════════════════════════════════════════
:: SENTINEL PRO KB5 — LAUNCHER
:: ══════════════════════════════════════════════════════════
:: Ce script lance l'intégralité de l'écosystème :
:: 1. Vérification de l'environnement Python
:: 2. Démarrage du Moteur Principal (Main Engine)
:: 3. Démarrage du Dashboard Interactif (Streamlit)
:: ══════════════════════════════════════════════════════════

echo.
echo [1/3] Verification de l'environnement...

:: Verifier Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [!] Erreur : Python n'est pas installe ou n'est pas dans le PATH.
    pause
    exit /b
)

:: Verifier les dépendances critiques
echo.
echo [2/3] Verification des modules (Tools/CheckImports)...
set PYTHONPATH=%CD%
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

:: Tenter une mise a jour de pip pour maximiser les chances de trouver des wheels
python -m pip install --upgrade pip setuptools wheel >nul 2>nul

python tools\check_imports.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo [!] Des modules sont manquants. Installation des dependances...
    echo [?] Note : Sur Python 3.14, la compilation peut prendre du temps.
    pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo.
        echo ----------------------------------------------------------
        echo [!] ERREUR CRITIQUE D'INSTALLATION
        echo ----------------------------------------------------------
        echo Votre version de Python (3.14) est trop recente pour avoir 
        echo des paquets pre-compiles (wheels).
        echo.
        echo SOLUTION : Vous DEVEZ installer les "Outils de build C++".
        echo.
        echo [?] Voulez-vous lancer l'installateur automatique maintenant ?
        set /p choice="Tapez 'O' pour Oui ou 'N' pour Non : "
        if /I "!choice!"=="O" (
            call install_compiler.bat
            exit /b
        )
        echo.
        echo Si vous preferez le faire manuellement :
        echo https://visualstudio.microsoft.com/visual-cpp-build-tools/
        echo ----------------------------------------------------------
        pause
        exit /b
    )
)

echo.
echo [3/3] Lancement des modules SENTINEL PRO...
echo -- Dossier racine : %~dp0
echo.

:: On utilise /D pour regler le dossier de travail sans s'emmeler avec les guillemets
echo -- Lancement du Moteur Engine (Console UI) --
start "SENTINEL ENGINE" /D "%~dp0" cmd /k "python main.py"

timeout /t 3 >nul

echo -- Lancement du War Room (Next-Gen Dash) --
start "SENTINEL WAR-ROOM" /D "%~dp0" cmd /k "python interface\war_room.py"

echo -- Lancement du Dashboard Streamlit (Legacy) --
start "SENTINEL DASHBOARD" /D "%~dp0" cmd /k "streamlit run interface\dashboard.py"

echo.
echo ----------------------------------------------------------
echo [OK] Tentative de lancement terminee.
echo.
echo Si les fenetres se sont fermees, vérifiez les erreurs ci-dessus.
echo ----------------------------------------------------------
echo.
pause
