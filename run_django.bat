@echo off
REM Change directory to where your Django project is located
cd /d "%~dp0"

REM Create and activate the virtual environment if it doesn't exist
if not exist venv (
    python -m venv venv
)

REM Activate the virtual environment
call venv\Scripts\activate

REM Install the required packages
pip install -r requirements.txt

REM Start the Django server
start "" /b "python" "manage.py" "runserver"

REM Open the default web browser to the Django server
start "" "http://127.0.0.1:8000"

REM Pause to keep the command prompt open
pause
