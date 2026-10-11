@echo off
setlocal
cd /d "%~dp0"
py -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
pyinstaller --noconfirm --clean --windowed --name OpenChess --icon "assets\OpenChess.ico" --add-data "assets\openchess-icon-1024.png;assets" --collect-all customtkinter --collect-all reportlab --collect-all openpyxl --collect-all xlrd run.py
echo.
echo Aplicacion generada en dist\OpenChess\OpenChess.exe
echo Para crear un instalador, abre installer\OpenChess.iss con Inno Setup y pulsa Compilar.
pause
