# Docker Hub Push Script for Smart Queue Management System (PowerShell)
# This script builds and pushes all microservice images to Docker Hub

param(
    [Parameter(Mandatory=$false)]
    [string]$DockerHubUsername
)

Write-Host "========================================" -ForegroundColor Green
Write-Host "Smart Queue Management System" -ForegroundColor Green
Write-Host "Docker Hub Push Script" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Get Docker Hub username if not provided
if (-not $DockerHubUsername) {
    $DockerHubUsername = Read-Host "Enter your Docker Hub username"
}

if (-not $DockerHubUsername) {
    Write-Host "Error: Docker Hub username is required!" -ForegroundColor Red
    exit 1
}

# Convert username to lowercase (Docker Hub requirement)
$DockerHubUsername = $DockerHubUsername.ToLower()

Write-Host "Docker Hub Username: $DockerHubUsername" -ForegroundColor Green
Write-Host ""

# Check if logged in to Docker Hub
$dockerInfo = docker info 2>&1
if (-not ($dockerInfo | Select-String -Pattern "Username")) {
    Write-Host "You are not logged in to Docker Hub." -ForegroundColor Yellow
    Write-Host "Please login to Docker Hub..." -ForegroundColor Yellow
    docker login
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Docker Hub login failed!" -ForegroundColor Red
        exit 1
    }
}

Write-Host "Successfully logged in to Docker Hub" -ForegroundColor Green
Write-Host ""

# Define image names and tags
$IMAGE_PREFIX = "${DockerHubUsername}/smartqueue"
$TAG = "latest"
$TIMESTAMP = Get-Date -Format "yyyyMMdd-HHmmss"
$VERSION_TAG = "${TAG}-${TIMESTAMP}"

Write-Host "Image prefix: $IMAGE_PREFIX" -ForegroundColor Green
Write-Host "Tags: $TAG, $VERSION_TAG" -ForegroundColor Green
Write-Host ""

# Function to build and push image
function Build-And-Push {
    param(
        [string]$ServiceName,
        [string]$ContextPath
    )
    
    $IMAGE_NAME = "${IMAGE_PREFIX}-${ServiceName}"
    
    Write-Host "Building $ServiceName service..." -ForegroundColor Yellow
    
    # Build the image
    $buildArgs = @(
        "build",
        "-t", "${IMAGE_NAME}:${TAG}",
        "-t", "${IMAGE_NAME}:${VERSION_TAG}",
        "-t", "${IMAGE_NAME}:dev",
        $ContextPath
    )
    
    & docker @buildArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to build $ServiceName" -ForegroundColor Red
        return $false
    }
    
    Write-Host "Successfully built $ServiceName" -ForegroundColor Green
    
    # Push the image
    Write-Host "Pushing $ServiceName to Docker Hub..." -ForegroundColor Yellow
    
    & docker push "${IMAGE_NAME}:${TAG}"
    & docker push "${IMAGE_NAME}:${VERSION_TAG}"
    & docker push "${IMAGE_NAME}:dev"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to push $ServiceName" -ForegroundColor Red
        return $false
    }
    
    Write-Host "Successfully pushed $ServiceName to Docker Hub" -ForegroundColor Green
    Write-Host "  Image: ${IMAGE_NAME}:${TAG}" -ForegroundColor Green
    Write-Host "  Image: ${IMAGE_NAME}:${VERSION_TAG}" -ForegroundColor Green
    Write-Host "  Image: ${IMAGE_NAME}:dev" -ForegroundColor Green
    Write-Host ""
    
    return $true
}

# Build and push all services
Write-Host "========================================" -ForegroundColor Green
Write-Host "Starting build and push process..." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

$FAILED_SERVICES = @()

# User Service
if (-not (Build-And-Push -ServiceName "user-service" -ContextPath "./user-service")) {
    $FAILED_SERVICES += "user-service"
}

# Queue Service
if (-not (Build-And-Push -ServiceName "queue-service" -ContextPath "./queue-service")) {
    $FAILED_SERVICES += "queue-service"
}

# Token Service
if (-not (Build-And-Push -ServiceName "token-service" -ContextPath "./token-service")) {
    $FAILED_SERVICES += "token-service"
}

# Notification Service
if (-not (Build-And-Push -ServiceName "notification-service" -ContextPath "./notification-service")) {
    $FAILED_SERVICES += "notification-service"
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Summary" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

if ($FAILED_SERVICES.Count -eq 0) {
    Write-Host "All services successfully pushed to Docker Hub!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your images are available at:" -ForegroundColor Green
    Write-Host "  ${IMAGE_PREFIX}-user-service:${TAG}" -ForegroundColor Cyan
    Write-Host "  ${IMAGE_PREFIX}-queue-service:${TAG}" -ForegroundColor Cyan
    Write-Host "  ${IMAGE_PREFIX}-token-service:${TAG}" -ForegroundColor Cyan
    Write-Host "  ${IMAGE_PREFIX}-notification-service:${TAG}" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To use these images in docker-compose.yml, update the image names:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "image: ${IMAGE_PREFIX}-user-service:${TAG}" -ForegroundColor White
    Write-Host "image: ${IMAGE_PREFIX}-queue-service:${TAG}" -ForegroundColor White
    Write-Host "image: ${IMAGE_PREFIX}-token-service:${TAG}" -ForegroundColor White
    Write-Host "image: ${IMAGE_PREFIX}-notification-service:${TAG}" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "Some services failed to push:" -ForegroundColor Red
    foreach ($service in $FAILED_SERVICES) {
        Write-Host "  - $service" -ForegroundColor Red
    }
    exit 1
}

Write-Host "Done!" -ForegroundColor Green
