@echo off
cd /d "%~dp0"
set CARREFOUR_SOCKET_ECOUTE=127.0.0.1
set CARREFOUR_SOCKET_PORT=5050
python serveur\main_serveur.py
pause
