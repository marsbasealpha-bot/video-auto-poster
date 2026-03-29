@echo off
TITLE Zero-Token Local Video Pipeline

:: 1. Activate Virtual Environment
IF EXIST "venv\Scripts\activate" (
    CALL venv\Scripts\activate
) ELSE (
    echo [ERROR] Virtual environment not found. Please run: python -m venv venv
    pause
    exit /b
)

:: 2. Launch Auto-Poster in a new window
echo Starting Video Auto-Poster...
start cmd /k "python main.py"

:: 3. Launch Story Processor (Bridge)
echo starting local Story Processor...
set /p AI_PATH="Enter your AI Render Output folder: "
python story_processor.py "%AI_PATH%"

pause
