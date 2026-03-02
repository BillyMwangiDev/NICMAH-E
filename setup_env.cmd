@echo off
SETLOCAL

echo Creating venv...
python -m venv venv
if errorlevel 1 (
    echo Venv creation failed.
    EXIT /b 1
)

echo Activating venv and installing requirements...
CALL venv\Scripts\activate.bat
if errorlevel 1 (
    echo Failed to activate venv.
    EXIT /b 1
)

pip install -r requirements.txt
if errorlevel 1 (
    echo Package installation failed.
    EXIT /b 1
)

echo Running migrations...
python manage.py migrate
if errorlevel 1 (
    echo Migrations failed.
    EXIT /b 1
)

echo Starting server...
python manage.py runserver

ENDLOCAL
EXIT /b 0
