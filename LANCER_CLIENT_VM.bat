@echo off
rem Lance l'interface de supervision en se connectant a la VM2.
rem A utiliser quand le projet tourne sur les deux VM Debian.
rem Pour une demonstration sur un seul PC, utilisez LANCER_CLIENT.bat.
cd /d "%~dp0"
set CARREFOUR_SOCKET_SERVEUR_HOTE=192.168.56.11
set CARREFOUR_SOCKET_PORT=5050
echo Connexion a la passerelle %CARREFOUR_SOCKET_SERVEUR_HOTE%:%CARREFOUR_SOCKET_PORT%
python client\main_client.py
pause
