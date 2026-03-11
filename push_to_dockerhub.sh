#!/usr/bin/env bash
# Docker Hub Push Script for Smart Queue Management System
# This script builds and pushes all microservice images to Docker Hub

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Smart Queue Management System${NC}"
echo -e "${GREEN}Docker Hub Push Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if Docker Hub username is provided
if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage: ./push_to_dockerhub.sh <docker_hub_username>${NC}"
    echo -e "${YELLOW}Example: ./push_to_dockerhub.sh myusername${NC}"
    echo ""
    read -p "Enter your Docker Hub username: " DOCKER_HUB_USERNAME
else
    DOCKER_HUB_USERNAME="$1"
fi

# Convert username to lowercase (Docker Hub requirement)
DOCKER_HUB_USERNAME=$(echo "$DOCKER_HUB_USERNAME" | tr '[:upper:]' '[:lower:]')

echo ""
echo -e "${GREEN}Docker Hub Username: ${DOCKER_HUB_USERNAME}${NC}"
echo ""

# Check if logged in to Docker Hub
if ! docker info 2>/dev/null | grep -q "Username"; then
    echo -e "${YELLOW}You are not logged in to Docker Hub.${NC}"
    echo -e "${YELLOW}Please login to Docker Hub...${NC}"
    docker login
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: Docker Hub login failed!${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}✓ Successfully logged in to Docker Hub${NC}"
echo ""

# Define image names and tags
IMAGE_PREFIX="${DOCKER_HUB_USERNAME}/smartqueue"
TAG="latest"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
VERSION_TAG="${TAG}-${TIMESTAMP}"

echo -e "${GREEN}Image prefix: ${IMAGE_PREFIX}${NC}"
echo -e "${GREEN}Tags: ${TAG}, ${VERSION_TAG}${NC}"
echo ""

# Function to build and push image
build_and_push() {
    local SERVICE_NAME=$1
    local CONTEXT_PATH=$2
    local IMAGE_NAME="${IMAGE_PREFIX}-${SERVICE_NAME}"
    
    echo -e "${YELLOW}Building ${SERVICE_NAME} service...${NC}"
    
    # Build the image
    docker build -t "${IMAGE_NAME}:${TAG}" \
                 -t "${IMAGE_NAME}:${VERSION_TAG}" \
                 -t "${IMAGE_NAME}:dev" \
                 ${CONTEXT_PATH}
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ Failed to build ${SERVICE_NAME}${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✓ Successfully built ${SERVICE_NAME}${NC}"
    
    # Push the image
    echo -e "${YELLOW}Pushing ${SERVICE_NAME} to Docker Hub...${NC}"
    
    docker push "${IMAGE_NAME}:${TAG}"
    docker push "${IMAGE_NAME}:${VERSION_TAG}"
    docker push "${IMAGE_NAME}:dev"
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ Failed to push ${SERVICE_NAME}${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✓ Successfully pushed ${SERVICE_NAME} to Docker Hub${NC}"
    echo -e "${GREEN}  Image: ${IMAGE_NAME}:${TAG}${NC}"
    echo -e "${GREEN}  Image: ${IMAGE_NAME}:${VERSION_TAG}${NC}"
    echo -e "${GREEN}  Image: ${IMAGE_NAME}:dev${NC}"
    echo ""
    
    return 0
}

# Build and push all services
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Starting build and push process...${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

FAILED_SERVICES=()

# User Service
build_and_push "user-service" "./user-service" || FAILED_SERVICES+=("user-service")

# Queue Service
build_and_push "queue-service" "./queue-service" || FAILED_SERVICES+=("queue-service")

# Token Service
build_and_push "token-service" "./token-service" || FAILED_SERVICES+=("token-service")

# Notification Service
build_and_push "notification-service" "./notification-service" || FAILED_SERVICES+=("notification-service")

# Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Summary${NC}"
echo -e "${GREEN}========================================${NC}"

if [ ${#FAILED_SERVICES[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ All services successfully pushed to Docker Hub!${NC}"
    echo ""
    echo -e "${GREEN}Your images are available at:${NC}"
    echo -e "  ${IMAGE_PREFIX}-user-service:${TAG}"
    echo -e "  ${IMAGE_PREFIX}-queue-service:${TAG}"
    echo -e "  ${IMAGE_PREFIX}-token-service:${TAG}"
    echo -e "  ${IMAGE_PREFIX}-notification-service:${TAG}"
    echo ""
    echo -e "${YELLOW}To use these images in docker-compose.yml, update the image names:${NC}"
    echo ""
    echo "image: ${IMAGE_PREFIX}-user-service:${TAG}"
    echo "image: ${IMAGE_PREFIX}-queue-service:${TAG}"
    echo "image: ${IMAGE_PREFIX}-token-service:${TAG}"
    echo "image: ${IMAGE_PREFIX}-notification-service:${TAG}"
    echo ""
else
    echo -e "${RED}✗ Some services failed to push:${NC}"
    for service in "${FAILED_SERVICES[@]}"; do
        echo -e "${RED}  - ${service}${NC}"
    done
    exit 1
fi

echo -e "${GREEN}Done!${NC}"
