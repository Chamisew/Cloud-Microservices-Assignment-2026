# Token Service - Smart Queue Management System

## Overview
The Token Service is a microservice responsible for generating and managing queue tokens in the Smart Queue Management System. It handles token creation, status updates, and integrates with the Notification Service to send alerts.

## Features
- Token generation with unique numbering system
- Token status management (active, called, completed, etc.)
- Integration with Notification Service for alerts
- RESTful API design
- Comprehensive error handling
- Health check endpoints
- Priority-based token management

## Core Integration Flow
The Token Service implements the critical integration workflow:

1. **POST /api/tokens/generate** - Core integration endpoint
   - Receives token request from Queue Service
   - Generates unique token with numbering system (Q001, Q002, etc.)
   - Saves token details to MongoDB Atlas
   - **CRUCIAL**: Calls Notification Service to send alert
   - Returns complete token information

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
- **Resilience Pattern**: Core functionality succeeds even if notification fails

## Prerequisites
- Python 3.9+
- MongoDB Atlas account
- Access to Notification Service (Port 5004)
- Docker (for containerization)

## Setup Instructions

### 1. Environment Configuration
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env file with your configuration
# Set MONGO_URI for MongoDB Atlas
# Set NOTIFICATION_SERVICE_URL
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
docker build -t token-service .

# Run container
docker run -p 5003:5003 \
  -e MONGO_URI="your_mongodb_connection_string" \
  -e NOTIFICATION_SERVICE_URL="http://notification-service:5004" \
  token-service
```

## API Endpoints

### Health Check
```
GET /health
```

### Token Management
```
POST /api/tokens/generate     # Generate new token (integration endpoint)
GET /api/tokens/{id}          # Get token by ID
GET /api/tokens/user/{user_id} # Get user tokens
PUT /api/tokens/status/{id}   # Update token status
```

## Integration Testing
The service includes comprehensive integration tests that mock the Notification Service:

```bash
# Run unit tests
python -m pytest tests/ -v

# Test token generation
curl -X POST http://localhost:5003/api/tokens/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_id_here",
    "queue_id": "queue_id_here",
    "user_name": "John Doe",
    "queue_name": "General Service"
  }'
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
| NOTIFICATION_SERVICE_URL | Notification Service URL | Yes |
| PORT | Application port (default: 5003) | No |
| SERVICE_API_KEY | Service-to-service authentication key | No |

## Database Collections
```javascript
// tokens collection
{
  "token_id": String,           // Unique token identifier
  "token_number": String,       // Human-readable number (Q001, Q002)
  "token_prefix": String,       // Token prefix for categorization
  "user_id": String,            // Associated user
  "queue_id": String,           // Associated queue
  "user_name": String,         // User name
  "queue_name": String,         // Queue name
  "service_type": String,      // general, priority, vip, emergency
  "status": String,            // active, called, serving, completed
  "priority": Integer,          // 1-4 priority level
  "created_at": DateTime,
  "updated_at": DateTime,
  "expires_at": DateTime,
  "called_at": DateTime,        // When called for service
  "completed_at": DateTime      // When service completed
}
```

## Error Handling
The service returns appropriate HTTP status codes:
- 200: Success
- 201: Created
- 400: Bad Request (validation errors)
- 404: Not Found
- 500: Internal Server Error

## Service Communication
The Token Service communicates with the Notification Service:

### Notification Service Integration
```python
# Send notification after token generation
notification_data = {
    'type': 'token_generated',
    'user_id': user_id,
    'user_name': user_name,
    'token_id': token_id,
    'token_number': token_number,
    'queue_name': queue_name,
    'service_type': service_type,
    'message': f"Token {token_number} generated for {user_name}"
}
response = requests.post(f"{NOTIFICATION_SERVICE_URL}/api/notifications/send", 
                        json=notification_data)
```

## Token Numbering System
- Uses prefix-based numbering (Q001, Q002, etc.)
- Automatic increment based on existing tokens
- Supports different prefixes for different queue types
- Ensures uniqueness within each prefix category

## Priority Management
- **General**: Priority 1 (default)
- **Priority**: Priority 2
- **VIP**: Priority 3
- **Emergency**: Priority 4

## Monitoring
Health check endpoint provides:
- Database connectivity status
- Notification Service connectivity
- Service uptime information
- Token generation statistics

## Performance Considerations
- Connection pooling for MongoDB
- Retry mechanism for service calls
- Exponential backoff for failed requests
- Efficient database indexing
- Request timeout configuration

## Resilience Pattern
The service implements graceful degradation:
- Token generation succeeds even if notification fails
- Core functionality is not dependent on external service availability
- Proper error logging and monitoring

## Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and security scans
5. Submit a pull request

## License
This project is part of the SLIIT SE4010 Cloud Computing assignment.