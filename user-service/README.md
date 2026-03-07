# User Service - Smart Queue Management System

## Overview
The User Service is a microservice responsible for managing user data in the Smart Queue Management System. It provides RESTful APIs for user registration, authentication, and profile management.

## Features
- User registration and profile management
- Email and phone number validation
- MongoDB Atlas integration with secure connection
- RESTful API design
- Comprehensive error handling
- Health check endpoint for monitoring
- Pagination support for user listings
- Soft delete functionality

## Security Features
- **Environment-based Configuration**: MongoDB credentials are loaded from environment variables
- **Input Validation**: Comprehensive data validation and sanitization
- **Secure Database Connection**: Connection pooling and timeout configuration
- **Error Handling**: Proper error responses without exposing sensitive information
- **Non-root Container User**: Docker container runs with limited privileges

## Prerequisites
- Python 3.9+
- MongoDB Atlas account (Free Tier)
- Docker (for containerization)

## Setup Instructions

### 1. Environment Configuration
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env file with your MongoDB Atlas credentials
# Get your connection string from MongoDB Atlas dashboard
```

### 2. Local Development Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

### 3. Docker Setup
```bash
# Build Docker image
docker build -t user-service .

# Run container
docker run -p 5001:5001 \
  -e MONGO_URI="your_mongodb_connection_string" \
  user-service
```

## API Endpoints

### Health Check
```
GET /health
```

### User Management
```
POST /api/users          # Create new user
GET /api/users           # Get all users (with pagination)
GET /api/users/{id}      # Get user by ID
PUT /api/users/{id}      # Update user
DELETE /api/users/{id}   # Delete user (soft delete)
```

## API Documentation
The service includes OpenAPI 3.0 specification in `swagger.yaml`. You can view the documentation using Swagger UI or any OpenAPI-compatible tool.

## Testing
```bash
# Run unit tests (if available)
python -m pytest tests/

# Test health endpoint
curl http://localhost:5001/health

# Test user creation
curl -X POST http://localhost:5001/api/users \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","email":"john@example.com","phone":"+94771234567"}'
```

## DevOps Features
- **CI/CD Pipeline**: GitHub Actions workflow with security scanning
- **Security Scanning**: Bandit and Safety tools for vulnerability detection
- **Code Quality**: Flake8 and PyLint integration
- **Docker Integration**: Multi-stage builds with security best practices
- **Monitoring**: Health check endpoints for container orchestration

## Environment Variables
| Variable | Description | Required |
|----------|-------------|----------|
| MONGO_URI | MongoDB Atlas connection string | Yes |
| PORT | Application port (default: 5001) | No |
| FLASK_ENV | Flask environment | No |
| SECRET_KEY | Application secret key | No |

## Database Schema
```javascript
{
  "_id": ObjectId,
  "name": String,
  "email": String,        // Unique
  "phone": String,        // Format: +94XXXXXXXXX
  "nic": String,          // Optional
  "created_at": DateTime,
  "updated_at": DateTime,
  "is_active": Boolean
}
```

## Error Handling
The service returns appropriate HTTP status codes:
- 200: Success
- 201: Created
- 400: Bad Request (validation errors)
- 404: Not Found
- 409: Conflict (duplicate email)
- 500: Internal Server Error
- 503: Service Unavailable

## Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and security scans
5. Submit a pull request

## License
This project is part of the SLIIT SE4010 Cloud Computing assignment.