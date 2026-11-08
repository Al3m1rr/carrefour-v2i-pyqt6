@echo off
rem Demarre les trois roles sur un seul PC (equivalent local des 2 VM).
cd /d "%~dp0"
start "VM1 - Moteur" cmd /k LANCER_MOTEUR.bat
timeout /t 3 /nobreak >nul
start "VM2 - Passerelle" cmd /k LANCER_PASSERELLE.bat
timeout /t 3 /nobreak >nul
start "Client PyQt6" cmd /k LANCER_CLIENT.bat
