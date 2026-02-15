@echo off
title Back2Work Bot Launcher
echo ==========================================
echo      Iniciando Back2Work Bot
echo ==========================================


cd /d "%~dp0"

if exist "%UserProfile%\anaconda3\Scripts\activate.bat" (
    call "%UserProfile%\anaconda3\Scripts\activate.bat"
) else (
    echo No encuentro Anaconda. Verifica la ruta en el .bat
    pause
    exit
)


call conda activate back2work


echo.
echo Lanzando la aplicacion
echo.

python -m streamlit run app/main.py

pause