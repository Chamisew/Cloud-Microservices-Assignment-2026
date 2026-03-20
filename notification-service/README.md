# Notification Service - Smart Queue Management System

## Overview
The Notification Service is the final microservice in the Smart Queue Management System chain. It handles all notification alerts and serves as the ultimate integration point, receiving alerts from the Token Service and persisting them to MongoDB Atlas.

## Features
- Notification creation and management
- Comprehensive input validation and sanitization
- Robust error handling to prevent service crashes
- RESTful API design
- Health check endpoints
- Notification statistics and analytics
- Pagination support for notification listings

## Core Integration Flow
The Notification Service implements the final integration workflow:

1. **POST /api/notifications/send** - Core integration endpoint (FINAL INTEGRATION POINT)
   - Receives notification requests from Token Service
   - Validates and sanitizes all input data
   - Saves notification records to MongoDB Atlas
   - Returns confirmation to Token Service

2. **Service Chain Completion**
   - **User Service (5001)** → **Queue Service (5002)** → **Token Service (5003)** → **Notification Service (5004)**
   - This is the final data persistence point in the integration chain

## Security Features
- **Environment-based Configuration**: MongoDB credentials loaded from environment variables
- **Input Validation**: Comprehensive data validation to prevent injection attacks
- **Data Sanitization**: Input sanitization to prevent malicious data processing
- **Error Handling**: Robust error handling to prevent service crashes from bad data
- **RESTful Design**: Proper HTTP status codes and response formats

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
docker build -t notification-service .

# Run container
docker run -p 5004:5004 \
  -e MONGO_URI="your_mongodb_connection_string" \
  notification-service
```

## API Endpoints

### Health Check
```
GET /health
```

### Notification Management
```
POST /api/notifications/send    # Send notification (FINAL integration endpoint)
GET /api/notifications          # Get notifications with filtering and pagination
GET /api/notifications/{id}     # Get specific notification
GET /api/notifications/stats    # Get notification statistics
```

## Integration Testing
The service includes comprehensive unit tests that verify robust error handling:

```bash
# Run unit tests
python -m pytest tests/ -v

# Test notification sending
curl -X POST http://localhost:5004/api/notifications/send \
  -H "Content-Type: application/json" \
  -d '{
    "type": "token_generated",
    "user_id": "user_id_here",
    "user_name": "John Doe",
    "token_id": "token_id_here",
    "token_number": "Q001",
    "queue_name": "General Service",
    "message": "Your token Q001 is ready in General Service"
  }'
```

## DevOps Features
- **CI/CD Pipeline**: GitHub Actions with security scanning
- **Security Scanning**: Bandit and Safety tools for vulnerability detection
- **Code Quality**: Flake8 and PyLint integration
- **Docker Integration**: Multi-stage builds with security best practices
- **Monitoring**: Health check endpoints for container orchestration

## Environment Variables
| Variable | Description | Required |
|----------|-------------|----------|
| MONGO_URI | MongoDB Atlas connection string | Yes |
| PORT | Application port (default: 5004) | No |
| FLASK_ENV | Flask environment | No |
| SECRET_KEY | Application secret key | No |

## Database Schema
```javascript
// notifications collection
{
  "notification_id": String,        // Unique notification identifier
  "type": String,                  // token_generated, token_called, etc.
  "user_id": String,               // User ID from User Service
  "user_name": String,            // User name
  "token_id": String,              // Token ID from Token Service
  "token_number": String,          // Token number (Q001, A-01, etc.)
  "queue_name": String,            // Queue name
  "message": String,               // Notification message
  "status": String,                // sent, delivered, failed, pending
  "priority": Integer,              // 1-5 priority level
  "service_type": String,          // general, priority, vip, emergency
  "created_at": DateTime,          // Notification creation timestamp
  "updated_at": DateTime,          // Last update timestamp
  "sent_at": DateTime              // When notification was processed
}
```

## Error Handling
The service implements robust error handling to prevent crashes:
- **Input Validation**: Comprehensive validation of all incoming data
- **Data Sanitization**: Cleaning and sanitizing input to prevent injection attacks
- **Graceful Degradation**: Service continues operating even with invalid data
- **Proper HTTP Responses**: Appropriate status codes for different error conditions

## Service Communication
The Notification Service receives data from the Token Service:

### Token Service Integration
```python
# Notification data structure from Token Service
notification_data = {
    'type': 'token_generated',
    'user_id': user_id,
    'user_name': user_name,
    'token_id': token_id,
    'token_number': token_number,
    'queue_name': queue_name,
    'message': f"Token {token_number} generated for {user_name}",
    'priority': priority
}
# This data is received via POST /api/notifications/send
```

## Input Validation
The service validates all incoming data:
- **Required Fields**: Checks for all mandatory fields
- **Data Types**: Validates ObjectId formats for user_id and token_id
- **String Lengths**: Validates user_name, queue_name, and message lengths
- **Enum Values**: Validates notification types and service types
- **Priority Range**: Validates priority values (1-5)

## Data Sanitization
The service sanitizes input data to prevent security issues:
- **Whitespace Removal**: Strips leading/trailing whitespace
- **Type Conversion**: Ensures proper data types
- **Malicious Content**: Handles potentially malicious input safely

## Monitoring
Health check endpoint provides:
- Database connectivity status
- Service role confirmation (final_integration_point)
- Timestamp and service information

## Performance Considerations
- Connection pooling for MongoDB
- Efficient database indexing
- Request timeout configuration
- Memory-efficient data processing

## Resilience Features
- **Error Isolation**: Errors in one request don't affect others
- **Input Robustness**: Handles malformed data gracefully
- **Database Recovery**: Continues operating with database issues
- **Logging**: Comprehensive logging for debugging and monitoring

## Testing Philosophy
The service includes tests for:
- **Normal Operation**: Valid data processing
- **Edge Cases**: Boundary conditions and unusual inputs
- **Error Conditions**: Invalid data and system errors
- **Security**: Input validation and sanitization
- **Integration**: Service-to-service communication

## Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and security scans
5. Submit a pull request

## License
This project is part of the SLIIT SE4010 Cloud Computing assignment.