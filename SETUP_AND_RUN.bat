@echo off
echo.
echo ================================================
echo Setting Up Smart Queue Management System
echo ================================================
echo.

cd /d "%~dp0"

echo Installing Python dependencies for all services...
echo.

REM Install dependencies for User Service
echo Installing User Service dependencies...
cd user-service
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt
echo User Service dependencies installed.
echo.

REM Install dependencies for Queue Service
echo Installing Queue Service dependencies...
cd ..\queue-service
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt
echo Queue Service dependencies installed.
echo.

REM Install dependencies for Token Service
echo Installing Token Service dependencies...
cd ..\token-service
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt
echo Token Service dependencies installed.
echo.

REM Install dependencies for Notification Service
echo Installing Notification Service dependencies...
cd ..\notification-service
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt
echo Notification Service dependencies installed.
echo.

REM Go back to root
cd ..

echo.
echo ================================================
echo Setup Complete!
echo ================================================
echo.
echo To run the services:
echo.
echo 1. Update the MONGO_URI in each service's .env file with your MongoDB Atlas connection string
echo 2. Run the START_SERVICES.bat file to start all services
echo.
echo MongoDB Atlas setup instructions:
echo   - Visit https://www.mongodb.com/cloud/atlas
echo   - Create a free cluster
echo   - Create a database user
echo   - Get your connection string
echo   - Update MONGO_URI in .env files
echo.
echo For local development with MongoDB Atlas:
echo   - Use connection string format:
echo     mongodb+srv://username:password@cluster-name.mongodb.net/database-name
echo.
echo Press any key to exit...
pause > nul