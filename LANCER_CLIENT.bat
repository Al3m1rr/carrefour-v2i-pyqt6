@echo off
cd /d "%~dp0"
set CARREFOUR_SOCKET_SERVEUR_HOTE=127.0.0.1
set CARREFOUR_SOCKET_PORT=5050
python client\main_client.py
pause
