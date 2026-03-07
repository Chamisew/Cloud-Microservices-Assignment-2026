# Queue Service - Smart Queue Management System

## Overview
The Queue Service is a microservice responsible for managing queue operations in the Smart Queue Management System. It handles queue creation, user assignments, and integrates with User and Token services for complete workflow management.

## Features
- Queue creation and management
- User assignment to queues
- Queue status monitoring
- Real-time occupancy tracking
- Service-to-service integration
- RESTful API design
- Comprehensive error handling
- Health check endpoints

## Integration Flow
The Queue Service implements a critical integration workflow:

1. **POST /api/queues/join** - Core integration endpoint
   - Calls User Service (Port 5001) to verify user exists
   - If user exists, calls Token Service (Port 5003) to generate token
   - Returns complete assignment with token information

2. **Service Communication**
   - Uses Python `requests` library for HTTP calls
   - Implements retry mechanism with exponential backoff
   - Circuit breaker pattern for resilience
   - Service-to-service authentication

## Security Features
- **Environment-based Configuration**: All service URLs and credentials from environment variables
- **Service Authentication**: X-Service-Key header for inter-service communication
- **Input Validation**: Comprehensive data validation and sanitization
- **Error Handling**: Proper error responses without exposing system details
- **Retry Logic**: Automatic retry with exponential backoff for failed service calls

## Prerequisites
- Python 3.9+
- MongoDB Atlas account
- Access to User Service (Port 5001) and Token Service (Port 5003)
- Docker (for containerization)

## Setup Instructions

### 1. Environment Configuration
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env file with your configuration
# Set MONGO_URI for MongoDB Atlas
# Set USER_SERVICE_URL and TOKEN_SERVICE_URL
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
docker build -t queue-service .

# Run container
docker run -p 5002:5002 \
  -e MONGO_URI="your_mongodb_connection_string" \
  -e USER_SERVICE_URL="http://user-service:5001" \
  -e TOKEN_SERVICE_URL="http://token-service:5003" \
  queue-service
```

## API Endpoints

### Health Check
```
GET /health
```

### Queue Management
```
POST /api/queues          # Create new queue
GET /api/queues           # Get all queues
GET /api/queues/{id}      # Get queue by ID
```

### Queue Assignment
```
POST /api/queues/join     # Join user to queue (integration endpoint)
GET /api/queues/assignments/{id}  # Get assignment details
```

## Integration Testing
The service includes comprehensive integration tests that mock external services:

```bash
# Run unit tests
python -m pytest tests/ -v

# Test integration flow
curl -X POST http://localhost:5002/api/queues/join \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user_id_here","queue_id":"queue_id_here"}'
```

## DevOps Features
- **CI/CD Pipeline**: GitHub Actions with security scanning
- **Security Scanning**: Bandit and Safety tools
- **Code Quality**: Flake8 and PyLint integration
- **Docker Integration**: Multi-stage builds with health checks
- **Service Monitoring**: Health endpoints with service connectivity status

## Environment Variables
| Variable | Description | Required |
|----------|-------------|----------|
| MONGO_URI | MongoDB Atlas connection string | Yes |
| USER_SERVICE_URL | User Service URL | Yes |
| TOKEN_SERVICE_URL | Token Service URL | Yes |
| PORT | Application port (default: 5002) | No |
| SERVICE_API_KEY | Service-to-service authentication key | No |

## Database Collections
```javascript
// queues collection
{
  "_id": ObjectId,
  "name": String,           // Unique queue name
  "description": String,
  "max_capacity": Integer,
  "current_count": Integer,
  "average_wait_time": Integer,
  "service_type": String,
  "status": String,         // active/inactive
  "created_at": DateTime,
  "updated_at": DateTime
}

// queue_assignments collection
{
  "_id": ObjectId,
  "user_id": String,
  "queue_id": String,
  "token_id": String,
  "user_name": String,
  "queue_name": String,
  "token_number": String,
  "status": String,         // waiting/serving/completed
  "joined_at": DateTime,
  "estimated_wait_time": Integer
}
```

## Error Handling
The service returns appropriate HTTP status codes:
- 200: Success
- 201: Created
- 400: Bad Request (validation errors)
- 404: Not Found
- 409: Conflict (duplicate name)
- 500: Internal Server Error
- 503: Service Unavailable (integration failures)

## Service Communication
The Queue Service communicates with other services:

### User Service Integration
```python
# Verify user exists
response = requests.get(f"{USER_SERVICE_URL}/api/users/{user_id}")
if response.status_code == 200:
    user_data = response.json()
```

### Token Service Integration
```python
# Generate queue token
token_data = {
    'user_id': user_id,
    'queue_id': queue_id,
    'user_name': user_name,
    'queue_name': queue_name
}
response = requests.post(f"{TOKEN_SERVICE_URL}/api/tokens/generate", json=token_data)
```

## Monitoring
Health check endpoint provides:
- Database connectivity status
- User Service connectivity
- Token Service connectivity
- Service uptime information

## Performance Considerations
- Connection pooling for MongoDB
- Retry mechanism for service calls
- Exponential backoff for failed requests
- Efficient database indexing
- Request timeout configuration

## Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and security scans
5. Submit a pull request

## License
This project is part of the SLIIT SE4010 Cloud Computing assignment.