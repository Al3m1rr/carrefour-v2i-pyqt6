@echo off
cd /d "%~dp0"
echo === Application Ambulance - Boitier embarque V2I ===
echo.
set CARREFOUR_SOCKET_SERVEUR_HOTE=127.0.0.1
set CARREFOUR_SOCKET_PORT=5050
python ambulance\main_ambulance.py
pause
