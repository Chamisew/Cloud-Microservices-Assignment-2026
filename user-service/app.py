"""
User Service - Smart Queue Management System
Port: 5001

This microservice manages user data including registration, authentication,
and user profile management. It integrates with MongoDB Atlas for data persistence
and follows DevSecOps best practices with environment-based configuration.

Security Features:
- Environment-based MongoDB connection (no hardcoded credentials)
- Input validation and sanitization
- Error handling without exposing sensitive information
- RESTful API design with proper HTTP status codes
"""

import os
import logging
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId
import re
from dotenv import load_dotenv
from functools import wraps
import time

# Load environment variables from .env file (for local development)
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing

# Configure logging for monitoring and debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database Configuration
# Security: Using environment variables to fetch MongoDB URI
# This prevents hardcoded credentials and follows DevSecOps best practices
MONGO_URI = os.environ.get('MONGO_URI')
if not MONGO_URI:
    logger.error("MONGO_URI environment variable not set")
    raise ValueError("MONGO_URI environment variable is required")

# Service Configuration
# Security: Using environment variables for service URLs and database connection
QUEUE_SERVICE_URL = os.environ.get('QUEUE_SERVICE_URL', 'http://localhost:5002')
TOKEN_SERVICE_URL = os.environ.get('TOKEN_SERVICE_URL', 'http://localhost:5003')
NOTIFICATION_SERVICE_URL = os.environ.get('NOTIFICATION_SERVICE_URL', 'http://localhost:5004')

MONGO_URI = os.environ.get('MONGO_URI')
if not MONGO_URI:
    logger.error("MONGO_URI environment variable not set")
    raise ValueError("MONGO_URI environment variable is required")

# MongoDB Connection
# Security: Connection pooling and timeout configuration for resilience
try:
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000,  # 5 second timeout
        maxPoolSize=50,                 # Connection pool size
        retryWrites=True               # Enable retryable writes
    )
    # Test connection
    client.admin.command('ping')
    db = client['smart_queue_db']
    users_collection = db['users']
    logger.info("Successfully connected to MongoDB Atlas")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise

# Input Validation Functions
def validate_email(email):
    """Validate email format using regex pattern"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """Validate phone number format (Sri Lankan format)"""
    pattern = r'^\+94\d{9}$'
    return re.match(pattern, phone) is not None

def validate_user_data(data):
    """
    Comprehensive validation of user input data
    Returns tuple: (is_valid, error_message)
    """
    required_fields = ['name', 'email', 'phone']
    
    # Check required fields
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"
    
    # Validate email format
    if not validate_email(data['email']):
        return False, "Invalid email format"
    
    # Validate phone format
    if not validate_phone(data['phone']):
        return False, "Invalid phone number format (use +94 format)"
    
    # Validate name length
    if len(data['name']) < 2 or len(data['name']) > 100:
        return False, "Name must be between 2 and 100 characters"
    
    return True, None

# Service Communication Utilities
def retry_on_failure(max_retries=3, delay=1):
    """
    Decorator for retrying failed service calls
    Implements circuit breaker pattern for resilience
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    last_exception = e
                    logger.warning(f"Service call attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
                    continue
            logger.error(f"All {max_retries} attempts failed for {func.__name__}")
            raise last_exception
        return wrapper
    return decorator

@retry_on_failure(max_retries=3, delay=1)
def call_queue_service(queue_data):
    """
    Call Queue Service to manage user queue operations
    Security: Uses service-to-service authentication
    """
    url = f"{QUEUE_SERVICE_URL}/api/queues/join"
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'User-Service/1.0'
    }
    
    # Add service authentication if API key is configured
    api_key = os.environ.get('SERVICE_API_KEY')
    if api_key:
        headers['X-Service-Key'] = api_key
    
    logger.info(f"Calling Queue Service: {url}")
    response = requests.post(url, json=queue_data, headers=headers, timeout=15)
    
    if response.status_code in [200, 201]:
        return response.json()
    else:
        logger.error(f"Queue Service error {response.status_code}: {response.text}")
        response.raise_for_status()

@retry_on_failure(max_retries=3, delay=1)
def call_token_service(token_data):
    """
    Call Token Service to generate tokens for user
    Security: Uses service-to-service authentication
    """
    url = f"{TOKEN_SERVICE_URL}/api/tokens/generate"
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'User-Service/1.0'
    }
    
    # Add service authentication if API key is configured
    api_key = os.environ.get('SERVICE_API_KEY')
    if api_key:
        headers['X-Service-Key'] = api_key
    
    logger.info(f"Calling Token Service: {url}")
    response = requests.post(url, json=token_data, headers=headers, timeout=15)
    
    if response.status_code in [200, 201]:
        return response.json()
    else:
        logger.error(f"Token Service error {response.status_code}: {response.text}")
        response.raise_for_status()

# API Routes

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring
    Returns service status and basic information
    """
    try:
        # Test database connection
        client.admin.command('ping')
        return jsonify({
            'status': 'healthy',
            'service': 'User Service',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected'
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'service': 'User Service',
            'error': 'Database connection failed'
        }), 503

@app.route('/api/users', methods=['POST'])
def create_user():
    """
    Create a new user in the system
    POST /api/users
    Request Body: {
        "name": "string",
        "email": "string",
        "phone": "string",
        "nic": "string" (optional)
    }
    Response: Created user object with ID
    """
    try:
        # Parse JSON data from request
        user_data = request.get_json()
        
        if not user_data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate input data
        is_valid, error_message = validate_user_data(user_data)
        if not is_valid:
            return jsonify({'error': error_message}), 400
        
        # Check if user already exists (email uniqueness)
        existing_user = users_collection.find_one({'email': user_data['email']})
        if existing_user:
            return jsonify({'error': 'User with this email already exists'}), 409
        
        # Add timestamps
        user_data['created_at'] = datetime.utcnow()
        user_data['updated_at'] = datetime.utcnow()
        user_data['is_active'] = True
        
        # Insert user into database
        # Security: Using insert_one with proper error handling
        result = users_collection.insert_one(user_data)
        
        # Prepare response (exclude sensitive data if needed)
        response_data = {
            'id': str(result.inserted_id),
            'name': user_data['name'],
            'email': user_data['email'],
            'phone': user_data['phone'],
            'created_at': user_data['created_at'].isoformat()
        }
        
        if 'nic' in user_data:
            response_data['nic'] = user_data['nic']
        
        logger.info(f"User created successfully: {result.inserted_id}")
        return jsonify(response_data), 201
        
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/users', methods=['GET'])
def get_users():
    """
    Retrieve all users (with pagination support)
    GET /api/users?page=1&limit=10
    Response: List of users with pagination metadata
    """
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        skip = (page - 1) * limit
        
        # Validate pagination parameters
        if page < 1 or limit < 1 or limit > 100:
            return jsonify({'error': 'Invalid pagination parameters'}), 400
        
        # Query database with pagination
        # Security: Using find with projection to limit returned fields
        cursor = users_collection.find(
            {'is_active': True},
            {
                'name': 1,
                'email': 1,
                'phone': 1,
                'nic': 1,
                'created_at': 1,
                '_id': 1
            }
        ).skip(skip).limit(limit).sort('created_at', -1)
        
        # Get total count for pagination metadata
        total_count = users_collection.count_documents({'is_active': True})
        
        # Convert cursor to list and format response
        users = []
        for user in cursor:
            user['_id'] = str(user['_id'])
            user['created_at'] = user['created_at'].isoformat()
            users.append(user)
        
        # Prepare paginated response
        response = {
            'users': users,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            }
        }
        
        logger.info(f"Retrieved {len(users)} users (page {page})")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error retrieving users: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/users/<user_id>', methods=['GET'])
def get_user(user_id):
    """
    Retrieve a specific user by ID
    GET /api/users/{user_id}
    Response: User object or 404 if not found
    """
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(user_id)
        except InvalidId:
            return jsonify({'error': 'Invalid user ID format'}), 400
        
        # Query database for user
        # Security: Using find_one with projection to limit returned fields
        user = users_collection.find_one(
            {'_id': object_id, 'is_active': True},
            {
                'name': 1,
                'email': 1,
                'phone': 1,
                'nic': 1,
                'created_at': 1,
                'updated_at': 1,
                '_id': 1
            }
        )
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Format response
        user['_id'] = str(user['_id'])
        user['created_at'] = user['created_at'].isoformat()
        user['updated_at'] = user['updated_at'].isoformat()
        
        logger.info(f"User retrieved: {user_id}")
        return jsonify(user), 200
        
    except Exception as e:
        logger.error(f"Error retrieving user {user_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    """
    Update an existing user
    PUT /api/users/{user_id}
    Request Body: Partial user data to update
    Response: Updated user object
    """
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(user_id)
        except InvalidId:
            return jsonify({'error': 'Invalid user ID format'}), 400
        
        # Parse update data
        update_data = request.get_json()
        if not update_data:
            return jsonify({'error': 'No update data provided'}), 400
        
        # Validate provided data
        if 'email' in update_data and not validate_email(update_data['email']):
            return jsonify({'error': 'Invalid email format'}), 400
        
        if 'phone' in update_data and not validate_phone(update_data['phone']):
            return jsonify({'error': 'Invalid phone number format'}), 400
        
        if 'name' in update_data and (len(update_data['name']) < 2 or len(update_data['name']) > 100):
            return jsonify({'error': 'Name must be between 2 and 100 characters'}), 400
        
        # Check if email already exists for another user
        if 'email' in update_data:
            existing_user = users_collection.find_one({
                'email': update_data['email'],
                '_id': {'$ne': object_id}
            })
            if existing_user:
                return jsonify({'error': 'Email already exists for another user'}), 409
        
        # Add update timestamp
        update_data['updated_at'] = datetime.utcnow()
        
        # Update user in database
        # Security: Using update_one with proper error handling
        result = users_collection.update_one(
            {'_id': object_id, 'is_active': True},
            {'$set': update_data}
        )
        
        if result.matched_count == 0:
            return jsonify({'error': 'User not found'}), 404
        
        # Retrieve updated user
        updated_user = users_collection.find_one(
            {'_id': object_id},
            {
                'name': 1,
                'email': 1,
                'phone': 1,
                'nic': 1,
                'created_at': 1,
                'updated_at': 1,
                '_id': 1
            }
        )
        
        # Format response
        updated_user['_id'] = str(updated_user['_id'])
        updated_user['created_at'] = updated_user['created_at'].isoformat()
        updated_user['updated_at'] = updated_user['updated_at'].isoformat()
        
        logger.info(f"User updated: {user_id}")
        return jsonify(updated_user), 200
        
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    """
    Soft delete a user (mark as inactive)
    DELETE /api/users/{user_id}
    Response: Success message
    """
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(user_id)
        except InvalidId:
            return jsonify({'error': 'Invalid user ID format'}), 400
        
        # Soft delete by setting is_active to False
        # Security: Using update_one for safe deletion
        result = users_collection.update_one(
            {'_id': object_id, 'is_active': True},
            {
                '$set': {
                    'is_active': False,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            return jsonify({'error': 'User not found'}), 404
        
        logger.info(f"User deleted (soft): {user_id}")
        return jsonify({'message': 'User deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/users/<user_id>/join-queue', methods=['POST'])
def join_queue(user_id):
    """
    Allow user to join a queue - Cross-service operation initiated from User Service
    POST /api/users/{user_id}/join-queue
    Request Body: {
        "queue_id": "string",
        "service_type": "string" (optional)
    }
    
    Integration Flow:
    1. Verify user exists locally
    2. Call Queue Service to join the queue
    3. Queue Service will call Token Service to generate token
    4. Return complete assignment information
    """
    try:
        # Validate user exists locally
        try:
            object_id = ObjectId(user_id)
        except InvalidId:
            return jsonify({'error': 'Invalid user ID format'}), 400
        
        user = users_collection.find_one(
            {'_id': object_id, 'is_active': True},
            {'name': 1, 'email': 1, 'phone': 1, '_id': 1}
        )
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Parse request data
        join_data = request.get_json()
        if not join_data:
            return jsonify({'error': 'No data provided'}), 400
        
        queue_id = join_data.get('queue_id')
        if not queue_id:
            return jsonify({'error': 'Missing queue_id'}), 400
        
        # Prepare data for Queue Service
        queue_request = {
            'user_id': user_id,
            'queue_id': queue_id,
            'service_type': join_data.get('service_type', 'general')
        }
        
        logger.info(f"Initiating queue join for user {user_id} via Queue Service")
        
        # Call Queue Service
        queue_response = call_queue_service(queue_request)
        
        logger.info(f"Queue join completed for user {user_id}")
        return jsonify({
            'message': 'Successfully joined queue',
            'user_id': user_id,
            'queue_assignment': queue_response
        }), 201
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Service communication error: {e}")
        return jsonify({'error': 'Service communication failed'}), 503
    except Exception as e:
        logger.error(f"Error initiating queue join: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/users/<user_id>/generate-token', methods=['POST'])
def generate_token_for_user(user_id):
    """
    Generate a token for a user - Direct integration with Token Service
    POST /api/users/{user_id}/generate-token
    Request Body: {
        "queue_id": "string",
        "queue_name": "string",
        "service_type": "string" (optional)
    }
    
    Integration Flow:
    1. Verify user exists locally
    2. Call Token Service to generate token
    3. Token Service will call Notification Service
    4. Return token information
    """
    try:
        # Validate user exists locally
        try:
            object_id = ObjectId(user_id)
        except InvalidId:
            return jsonify({'error': 'Invalid user ID format'}), 400
        
        user = users_collection.find_one(
            {'_id': object_id, 'is_active': True},
            {'name': 1, '_id': 1}
        )
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Parse request data
        token_data = request.get_json()
        if not token_data:
            return jsonify({'error': 'No data provided'}), 400
        
        queue_id = token_data.get('queue_id')
        queue_name = token_data.get('queue_name')
        
        if not queue_id or not queue_name:
            return jsonify({'error': 'Missing required fields: queue_id, queue_name'}), 400
        
        # Prepare data for Token Service
        token_request = {
            'user_id': user_id,
            'queue_id': queue_id,
            'user_name': user.get('name', 'Unknown'),
            'queue_name': queue_name,
            'service_type': token_data.get('service_type', 'general')
        }
        
        logger.info(f"Generating token for user {user_id} via Token Service")
        
        # Call Token Service
        token_response = call_token_service(token_request)
        
        logger.info(f"Token generated for user {user_id}: {token_response.get('token_id')}")
        return jsonify({
            'message': 'Token generated successfully',
            'user_id': user_id,
            'token': token_response
        }), 201
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Service communication error: {e}")
        return jsonify({'error': 'Service communication failed'}), 503
    except Exception as e:
        logger.error(f"Error generating token: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Error Handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 Not Found errors"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

# Application startup
if __name__ == '__main__':
    # Get port from environment variable or default to 5001
    port = int(os.environ.get('PORT', 5001))
    
    logger.info(f"Starting User Service on port {port}")
    logger.info("Database connection established")
    logger.info("Ready to serve requests")
    
    # Run the Flask application
    # Security: Debug mode should be False in production
    app.run(host='0.0.0.0', port=port, debug=False)