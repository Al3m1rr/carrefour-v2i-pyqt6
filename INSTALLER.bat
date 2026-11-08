@echo off
cd /d "%~dp0"
echo Installation des dependances...
python -m pip install PyQt6 mysql-connector-python matplotlib
echo.
echo Termine. Vous pouvez lancer LANCER_TOUT.bat
pause
