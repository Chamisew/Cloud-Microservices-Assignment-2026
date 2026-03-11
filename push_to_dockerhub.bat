@echo off
REM Docker Hub Push Script for Smart Queue Management System (Batch)
REM This script builds and pushes all microservice images to Docker Hub

echo ========================================
echo Smart Queue Management System
echo Docker Hub Push Script
echo ========================================
echo.

set /p DOCKER_HUB_USERNAME="Enter your Docker Hub username: "

if "%DOCKER_HUB_USERNAME%"=="" (
    echo Error: Docker Hub username is required!
    pause
    exit /b 1
)

echo.
echo Docker Hub Username: %DOCKER_HUB_USERNAME%
echo.

REM Check if logged in to Docker Hub
docker info | findstr /C:"Username" >nul 2>&1
if errorlevel 1 (
    echo You are not logged in to Docker Hub.
    echo Please login to Docker Hub...
    docker login
    if errorlevel 1 (
        echo Error: Docker Hub login failed!
        pause
        exit /b 1
    )
)

echo ✓ Successfully logged in to Docker Hub
echo.

REM Define image names and tags
set IMAGE_PREFIX=%DOCKER_HUB_USERNAME%/smartqueue
set TAG=latest

REM Get timestamp for version tag
for /f "tokens=2 delims==" %%i in ('wmic os get localdatetime /value') do set datetime=%%i
set VERSION_TAG=%TAG%-%datetime:~0,8%-%datetime:~8,6%

echo Image prefix: %IMAGE_PREFIX%
echo Tags: %TAG%, %VERSION_TAG%
echo.

REM Function to build and push image
:build_and_push
set SERVICE_NAME=%1
set CONTEXT_PATH=%2
set IMAGE_NAME=%IMAGE_PREFIX%-%SERVICE_NAME%

echo Building %SERVICE_NAME% service...

docker build -t "%IMAGE_NAME%:%TAG%" -t "%IMAGE_NAME%:%VERSION_TAG%" -t "%IMAGE_NAME%:dev" %CONTEXT_PATH%
if errorlevel 1 (
    echo ✗ Failed to build %SERVICE_NAME%
    goto :failed
)

echo ✓ Successfully built %SERVICE_NAME%

echo Pushing %SERVICE_NAME% to Docker Hub...

docker push "%IMAGE_NAME%:%TAG%"
docker push "%IMAGE_NAME%:%VERSION_TAG%"
docker push "%IMAGE_NAME%:dev%"
if errorlevel 1 (
    echo ✗ Failed to push %SERVICE_NAME%
    goto :failed
)

echo ✓ Successfully pushed %SERVICE_NAME% to Docker Hub
echo   Image: %IMAGE_NAME%:%TAG%
echo   Image: %IMAGE_NAME%:%VERSION_TAG%
echo   Image: %IMAGE_NAME%:dev
echo.

goto :eof

:failed
set FAILED_SERVICES=%FAILED_SERVICES% %SERVICE_NAME%
goto :eof

REM Build and push all services
echo ========================================
echo Starting build and push process...
echo ========================================
echo.

set FAILED_SERVICES=

call :build_and_push "user-service" "./user-service"
call :build_and_push "queue-service" "./queue-service"
call :build_and_push "token-service" "./token-service"
call :build_and_push "notification-service" "./notification-service"

REM Summary
echo.
echo ========================================
echo Summary
echo ========================================

if "%FAILED_SERVICES%"=="" (
    echo ✓ All services successfully pushed to Docker Hub!
    echo.
    echo Your images are available at:
    echo   %IMAGE_PREFIX%-user-service:%TAG%
    echo   %IMAGE_PREFIX%-queue-service:%TAG%
    echo   %IMAGE_PREFIX%-token-service:%TAG%
    echo   %IMAGE_PREFIX%-notification-service:%TAG%
    echo.
    echo To use these images in docker-compose.yml, update the image names:
    echo.
    echo image: %IMAGE_PREFIX%-user-service:%TAG%
    echo image: %IMAGE_PREFIX%-queue-service:%TAG%
    echo image: %IMAGE_PREFIX%-token-service:%TAG%
    echo image: %IMAGE_PREFIX%-notification-service:%TAG%
    echo.
) else (
    echo ✗ Some services failed to push:%FAILED_SERVICES%
    pause
    exit /b 1
)

echo Done!
pause
