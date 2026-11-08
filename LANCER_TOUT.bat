@echo off
cd /d "%~dp0"
start "Serveur carrefour" cmd /k LANCER_SERVEUR.bat
timeout /t 3 /nobreak >nul
start "Client carrefour" cmd /k LANCER_CLIENT.bat
