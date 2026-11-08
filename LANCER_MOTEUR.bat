@echo off
rem Role de la VM1 "Simulation", lance ici en local pour les tests.
cd /d "%~dp0"
set CARREFOUR_MOTEUR_ECOUTE=127.0.0.1
set CARREFOUR_MOTEUR_PORT=5051
python serveur\main_moteur.py
pause
