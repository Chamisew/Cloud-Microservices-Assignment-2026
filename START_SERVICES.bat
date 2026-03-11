@echo off
echo.
echo ================================================
echo Starting Smart Queue Management System Services
echo ================================================
echo.

echo Checking if Python dependencies are installed...

REM Check if flask is installed
python -c "import flask" 2>nul
if errorlevel 1 (
    echo Flask is not installed. Please run SETUP_AND_RUN.bat first.
    pause
    exit /b 1
)

REM Check if pymongo is installed
python -c "import pymongo" 2>nul
if errorlevel 1 (
    echo pymongo is not installed. Please run SETUP_AND_RUN.bat first.
    pause
    exit /b 1
)

REM Check if python-dotenv is installed
python -c "import dotenv" 2>nul
if errorlevel 1 (
    echo python-dotenv is not installed. Please run SETUP_AND_RUN.bat first.
    pause
    exit /b 1
)

echo All required dependencies are installed.
echo.

REM Create a virtual environment and install dependencies for each service
echo Setting up Python virtual environments...

cd /d "%~dp0"

REM Setup User Service
echo.
echo Setting up User Service (Port 5001)...
cd user-service
if not exist venv (
    echo Creating virtual environment for User Service...
    python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt > nul 2>&1
echo User Service setup complete.

REM Setup Queue Service  
echo.
echo Setting up Queue Service (Port 5002)...
cd ..\queue-service
if not exist venv (
    echo Creating virtual environment for Queue Service...
    python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt > nul 2>&1
echo Queue Service setup complete.

REM Setup Token Service
echo.
echo Setting up Token Service (Port 5003)...
cd ..\token-service
if not exist venv (
    echo Creating virtual environment for Token Service...
    python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt > nul 2>&1
echo Token Service setup complete.

REM Setup Notification Service
echo.
echo Setting up Notification Service (Port 5004)...
cd ..\notification-service
if not exist venv (
    echo Creating virtual environment for Notification Service...
    python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt > nul 2>&1
echo Notification Service setup complete.

REM Go back to root
cd ..

echo.
echo ================================================
echo Starting Services in Background...
echo ================================================
echo.

REM Start User Service in background
echo Starting User Service on Port 5001...
start "User Service" cmd /k "cd /d \"%~dp0user-service\" && venv\Scripts\activate && set MONGO_URI=mongodb+srv://your_username:your_password@cluster0.example.mongodb.net/smart_queue_db?retryWrites=true&w=majority && echo Starting User Service... && python app.py"

timeout /t 3 /nobreak > nul

REM Start Queue Service in background  
echo Starting Queue Service on Port 5002...
start "Queue Service" cmd /k "cd /d \"%~dp0queue-service\" && venv\Scripts\activate && set MONGO_URI=mongodb+srv://your_username:your_password@cluster0.example.mongodb.net/smart_queue_db?retryWrites=true&w=majority&& set USER_SERVICE_URL=http://localhost:5001&& set TOKEN_SERVICE_URL=http://localhost:5003&& echo Starting Queue Service... && python app.py"

timeout /t 3 /nobreak > nul

REM Start Token Service in background
echo Starting Token Service on Port 5003...
start "Token Service" cmd /k "cd /d \"%~dp0token-service\" && venv\Scripts\activate && set MONGO_URI=mongodb+srv://your_username:your_password@cluster0.example.mongodb.net/smart_queue_db?retryWrites=true&w=majority&& set NOTIFICATION_SERVICE_URL=http://localhost:5004&& echo Starting Token Service... && python app.py"

timeout /t 3 /nobreak > nul

REM Start Notification Service in background
echo Starting Notification Service on Port 5004...
start "Notification Service" cmd /k "cd /d \"%~dp0notification-service\" && venv\Scripts\activate && set MONGO_URI=mongodb+srv://your_username:your_password@cluster0.example.mongodb.net/smart_queue_db?retryWrites=true&w=majority&& echo Starting Notification Service... && python app.py"

echo.
echo ================================================
echo Services Started Successfully!
echo ================================================
echo.
echo Access the services at:
echo   User Service: http://localhost:5001/health
echo   Queue Service: http://localhost:5002/health  
echo   Token Service: http://localhost:5003/health
echo   Notification Service: http://localhost:5004/health
echo.
echo NOTE: 
echo   1. Update MONGO_URI in each service's .env file with your MongoDB Atlas connection string
echo   2. Four separate command prompt windows have opened, one for each service
echo   3. To stop services, close their respective command prompt windows
echo.
pause