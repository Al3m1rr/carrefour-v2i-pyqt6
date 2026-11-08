@echo off
rem Installe les dependances du poste client, aux versions exactes
rem listees dans requirements.txt.
cd /d "%~dp0"
echo Installation des dependances du poste client...
echo.
python -m pip install -r requirements.txt
echo.
echo Termine. Vous pouvez lancer :
echo   LANCER_TOUT.bat       pour une demonstration sur ce seul PC
echo   LANCER_CLIENT_VM.bat  pour se connecter aux deux VM
pause
