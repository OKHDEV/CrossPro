@echo off
cd /d "%~dp0"
python -m pip install pyinstaller pillow
python -m PyInstaller --onefile --noconsole --clean --name CrossPro crosspro.py
echo dist\CrossPro.exe build done
pause
