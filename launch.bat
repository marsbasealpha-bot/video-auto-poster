@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
start /b python main.py
start pythonw watch_window.pyw
