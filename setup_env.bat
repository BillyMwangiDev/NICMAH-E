@echo off
echo Creating venv...
python -m venv venv
if errorlevel 1 (
    echo Venv creation failed.
    exit /b 1
)
echo Activating venv and installing requirements...
call venv\Scripts\activate
pip install -r requirements.txt
echo Running migrations...
python manage.py migrate
echo Starting server...
python manage.py runserver
