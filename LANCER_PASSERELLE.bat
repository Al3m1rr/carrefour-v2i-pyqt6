@echo off
rem Role de la VM2 "Passerelle", lance ici en local pour les tests.
cd /d "%~dp0"
set CARREFOUR_MOTEUR_HOTE=127.0.0.1
set CARREFOUR_MOTEUR_PORT=5051
set CARREFOUR_SOCKET_ECOUTE=127.0.0.1
set CARREFOUR_SOCKET_PORT=5050
python serveur\main_passerelle.py
pause
