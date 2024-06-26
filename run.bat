@echo off
echo Setting up the Django environment...

:: Navigate to the Django project directory
cd C:\Dashboard\tco_ui\tco_ui\tco

:: Activate the virtual environment (adjust the path if needed)
call venv\Scripts\activate

:: Install requirements (if needed)
echo Installing requirements...
pip install -r requirements.txt

REM Set the PYTHONPATH environment variable to the current directory
set PYTHONPATH=%cd%

:: Make migrations and migrate the database
echo Making migrations...
python manage.py makemigrations
python manage.py migrate

:: Run the Django development server
echo Starting the Django development server...
start python manage.py runserver

:: Create a zip file of the project (excluding the virtual environment and other unnecessary files)
echo Creating a zip file of the project...
powershell Compress-Archive -Path .\* -DestinationPath ..\tco_ui_project.zip -Exclude *.pyc,*.pyo,*.log,venv\*,__pycache__\*

echo Done! The server is running and the project has been zipped.
pause
