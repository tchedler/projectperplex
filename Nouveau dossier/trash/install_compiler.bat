@echo off
TITLE SENTINEL PRO — INSTALLATEUR COMPILATEUR C++
setlocal enabledelayedexpansion

echo.
echo ══════════════════════════════════════════════════════════
echo INSTALLATEUR AUTOMATIQUE DES OUTILS DE BUILD C++
echo ══════════════════════════════════════════════════════════
echo.
echo [!] NOTE : Cette operation necessite environ 3 Go d'espace.
echo [!] Une fenetre de confirmation Windows (UAC) va s'ouvrir.
echo.
echo [1/2] Lancement de l'installation via winget...
echo.

:: Commande winget pour installer les Build Tools avec le workload Desktop C++
winget install --id Microsoft.VisualStudio.2022.BuildTools --override "--add Microsoft.VisualStudio.Workload.NativeDesktop --includeRecommended --passive --norestart" --accept-package-agreements --accept-source-agreements

if %ERRORLEVEL% neq 0 (
    echo.
    echo [!] L'installation a echoue ou a ete annulee.
    echo [?] Essayez de l'executer en tant qu'administrateur.
    pause
    exit /b
)

echo.
echo [2/2] Installation terminee !
echo.
echo Vous pouvez maintenant relancer LAUNCH_SENTINEL.bat
echo.
pause
