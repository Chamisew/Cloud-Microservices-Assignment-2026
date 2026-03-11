@echo off
echo.
echo ================================================
echo Smart Queue Management System - Status Check
echo ================================================
echo.

echo Checking Docker container status...
docker-compose ps

echo.
echo ================================================
echo To restart the system if containers stopped:
echo ================================================
echo.
echo 1. If containers are "Exited", run: docker-compose down
echo 2. Then run: docker-compose up -d
echo.
echo If services are still running, they should be accessible at:
echo   - User Service: http://localhost:5001/health
echo   - Queue Service: http://localhost:5002/health
echo   - Token Service: http://localhost:5003/health
echo   - Notification Service: http://localhost:5004/health
echo   - MongoDB Express: http://localhost:8081
echo.
echo Press any key to exit...
pause > nul