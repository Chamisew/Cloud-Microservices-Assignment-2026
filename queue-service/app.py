"""
Queue Service - Smart Queue Management System
Port: 5002

This microservice manages queue operations including:
- Queue creation and management
- User assignment to queues
- Queue status monitoring
- Inter-service communication with User and Token services

Integration Flow:
1. POST /queues/join calls User Service (Port 5001) to verify user exists
2. If user exists, calls Token Service (Port 5003) to generate token
3. Returns complete queue assignment with token information

Security Features:
- Environment-based MongoDB connection (no hardcoded credentials)
- Service-to-service authentication
- Input validation and error handling
- Circuit breaker pattern for external service calls
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

# Service Configuration
# Security: Using environment variables for service URLs and database connection
USER_SERVICE_URL = os.environ.get('USER_SERVICE_URL', 'http://localhost:5001')
TOKEN_SERVICE_URL = os.environ.get('TOKEN_SERVICE_URL', 'http://localhost:5003')
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
    queues_collection = db['queues']
    queue_assignments_collection = db['queue_assignments']
    logger.info("Successfully connected to MongoDB Atlas")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise

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
def call_user_service(user_id):
    """
    Call User Service to verify user exists
    Security: Uses service-to-service authentication if configured
    """
    url = f"{USER_SERVICE_URL}/api/users/{user_id}"
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Queue-Service/1.0'
    }
    
    # Add service authentication if API key is configured
    api_key = os.environ.get('SERVICE_API_KEY')
    if api_key:
        headers['X-Service-Key'] = api_key
    
    logger.info(f"Calling User Service: {url}")
    response = requests.get(url, headers=headers, timeout=10)
    
    if response.status_code == 200:
        user_data = response.json()
        logger.info(f"User verified: {user_id}")
        return user_data
    elif response.status_code == 404:
        logger.warning(f"User not found: {user_id}")
        return None
    else:
        logger.error(f"User Service error {response.status_code}: {response.text}")
        response.raise_for_status()

@retry_on_failure(max_retries=3, delay=1)
def call_token_service(token_request_data):
    """
    Call Token Service to generate queue token
    Security: Uses service-to-service authentication
    """
    url = f"{TOKEN_SERVICE_URL}/api/tokens/generate"
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Queue-Service/1.0'
    }
    
    # Add service authentication if API key is configured
    api_key = os.environ.get('SERVICE_API_KEY')
    if api_key:
        headers['X-Service-Key'] = api_key
    
    logger.info(f"Calling Token Service: {url}")
    response = requests.post(url, json=token_request_data, headers=headers, timeout=15)
    
    if response.status_code == 201:
        token_data = response.json()
        logger.info(f"Token generated: {token_data.get('token_id')}")
        return token_data
    else:
        logger.error(f"Token Service error {response.status_code}: {response.text}")
        response.raise_for_status()

# Input Validation Functions
def validate_queue_data(data):
    """
    Validate queue creation/update data
    Returns tuple: (is_valid, error_message)
    """
    required_fields = ['name', 'description']
    
    # Check required fields
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"
    
    # Validate name length
    if len(data['name']) < 3 or len(data['name']) > 50:
        return False, "Queue name must be between 3 and 50 characters"
    
    # Validate description length
    if len(data['description']) < 10 or len(data['description']) > 200:
        return False, "Description must be between 10 and 200 characters"
    
    # Validate max_capacity if provided
    if 'max_capacity' in data:
        try:
            capacity = int(data['max_capacity'])
            if capacity < 1 or capacity > 1000:
                return False, "Max capacity must be between 1 and 1000"
        except (ValueError, TypeError):
            return False, "Max capacity must be a valid number"
    
    return True, None

def validate_join_queue_data(data):
    """
    Validate queue join request data
    Returns tuple: (is_valid, error_message)
    """
    required_fields = ['user_id', 'queue_id']
    
    # Check required fields
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"
    
    # Validate ObjectId format
    try:
        ObjectId(data['user_id'])
        ObjectId(data['queue_id'])
    except InvalidId:
        return False, "Invalid user_id or queue_id format"
    
    return True, None

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
        
        # Test service connectivity
        services_status = {}
        try:
            requests.get(f"{USER_SERVICE_URL}/health", timeout=3)
            services_status['user_service'] = 'connected'
        except:
            services_status['user_service'] = 'disconnected'
            
        try:
            requests.get(f"{TOKEN_SERVICE_URL}/health", timeout=3)
            services_status['token_service'] = 'connected'
        except:
            services_status['token_service'] = 'disconnected'
        
        return jsonify({
            'status': 'healthy',
            'service': 'Queue Service',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'services': services_status
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'service': 'Queue Service',
            'error': str(e)
        }), 503

@app.route('/api/queues', methods=['POST'])
def create_queue():
    """
    Create a new queue
    POST /api/queues
    Request Body: {
        "name": "string",
        "description": "string",
        "max_capacity": "integer" (optional, default: 50),
        "service_type": "string" (optional)
    }
    Response: Created queue object with ID
    """
    try:
        # Parse JSON data from request
        queue_data = request.get_json()
        
        if not queue_data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate input data
        is_valid, error_message = validate_queue_data(queue_data)
        if not is_valid:
            return jsonify({'error': error_message}), 400
        
        # Check if queue name already exists
        existing_queue = queues_collection.find_one({'name': queue_data['name']})
        if existing_queue:
            return jsonify({'error': 'Queue with this name already exists'}), 409
        
        # Set default values
        queue_data['max_capacity'] = int(queue_data.get('max_capacity', 50))
        queue_data['current_count'] = 0
        queue_data['average_wait_time'] = 0
        queue_data['status'] = 'active'
        queue_data['created_at'] = datetime.utcnow()
        queue_data['updated_at'] = datetime.utcnow()
        
        # Insert queue into database
        result = queues_collection.insert_one(queue_data)
        
        # Prepare response
        response_data = {
            'id': str(result.inserted_id),
            'name': queue_data['name'],
            'description': queue_data['description'],
            'max_capacity': queue_data['max_capacity'],
            'current_count': queue_data['current_count'],
            'status': queue_data['status'],
            'created_at': queue_data['created_at'].isoformat()
        }
        
        if 'service_type' in queue_data:
            response_data['service_type'] = queue_data['service_type']
        
        logger.info(f"Queue created successfully: {result.inserted_id}")
        return jsonify(response_data), 201
        
    except Exception as e:
        logger.error(f"Error creating queue: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/queues', methods=['GET'])
def get_queues():
    """
    Retrieve all queues with current status
    GET /api/queues
    Response: List of queues with current occupancy and wait times
    """
    try:
        # Query database for active queues
        cursor = queues_collection.find(
            {'status': 'active'},
            {
                'name': 1,
                'description': 1,
                'max_capacity': 1,
                'current_count': 1,
                'average_wait_time': 1,
                'service_type': 1,
                'created_at': 1,
                '_id': 1
            }
        ).sort('created_at', -1)
        
        # Convert cursor to list and format response
        queues = []
        for queue in cursor:
            queue['_id'] = str(queue['_id'])
            queue['created_at'] = queue['created_at'].isoformat()
            
            # Calculate occupancy percentage
            if queue['max_capacity'] > 0:
                queue['occupancy_percentage'] = round(
                    (queue['current_count'] / queue['max_capacity']) * 100, 2
                )
            else:
                queue['occupancy_percentage'] = 0
            
            queues.append(queue)
        
        logger.info(f"Retrieved {len(queues)} queues")
        return jsonify({'queues': queues}), 200
        
    except Exception as e:
        logger.error(f"Error retrieving queues: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/queues/<queue_id>', methods=['GET'])
def get_queue(queue_id):
    """
    Retrieve a specific queue by ID
    GET /api/queues/{queue_id}
    Response: Queue object with detailed information
    """
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(queue_id)
        except InvalidId:
            return jsonify({'error': 'Invalid queue ID format'}), 400
        
        # Query database for queue
        queue = queues_collection.find_one(
            {'_id': object_id, 'status': 'active'},
            {
                'name': 1,
                'description': 1,
                'max_capacity': 1,
                'current_count': 1,
                'average_wait_time': 1,
                'service_type': 1,
                'created_at': 1,
                'updated_at': 1,
                '_id': 1
            }
        )
        
        if not queue:
            return jsonify({'error': 'Queue not found'}), 404
        
        # Format response
        queue['_id'] = str(queue['_id'])
        queue['created_at'] = queue['created_at'].isoformat()
        queue['updated_at'] = queue['updated_at'].isoformat()
        
        # Calculate occupancy percentage
        if queue['max_capacity'] > 0:
            queue['occupancy_percentage'] = round(
                (queue['current_count'] / queue['max_capacity']) * 100, 2
            )
        else:
            queue['occupancy_percentage'] = 0
        
        logger.info(f"Queue retrieved: {queue_id}")
        return jsonify(queue), 200
        
    except Exception as e:
        logger.error(f"Error retrieving queue {queue_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/queues/join', methods=['POST'])
def join_queue():
    """
    Join a user to a queue - Core Integration Endpoint
    POST /api/queues/join
    Request Body: {
        "user_id": "string",
        "queue_id": "string",
        "service_type": "string" (optional)
    }
    
    Integration Flow:
    1. Verify user exists by calling User Service (GET /users/{user_id})
    2. If user exists, call Token Service to generate token (POST /tokens/generate)
    3. Return complete assignment with token information
    
    Response: Queue assignment with token details
    """
    try:
        # Parse request data
        join_data = request.get_json()
        
        if not join_data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate input data
        is_valid, error_message = validate_join_queue_data(join_data)
        if not is_valid:
            return jsonify({'error': error_message}), 400
        
        user_id = join_data['user_id']
        queue_id = join_data['queue_id']
        
        # Step 1: Verify user exists by calling User Service
        logger.info(f"Step 1: Verifying user {user_id} with User Service")
        user_data = call_user_service(user_id)
        
        if not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        # Step 2: Verify queue exists and get queue details
        logger.info(f"Step 2: Verifying queue {queue_id}")
        try:
            queue_object_id = ObjectId(queue_id)
        except InvalidId:
            return jsonify({'error': 'Invalid queue ID format'}), 400
        
        queue_data = queues_collection.find_one(
            {'_id': queue_object_id, 'status': 'active'}
        )
        
        if not queue_data:
            return jsonify({'error': 'Queue not found or inactive'}), 404
        
        # Check queue capacity
        if queue_data['current_count'] >= queue_data['max_capacity']:
            return jsonify({'error': 'Queue is at maximum capacity'}), 400
        
        # Step 3: Call Token Service to generate token
        logger.info(f"Step 3: Generating token with Token Service")
        token_request = {
            'user_id': user_id,
            'queue_id': queue_id,
            'user_name': user_data.get('name', 'Unknown'),
            'queue_name': queue_data.get('name', 'Unknown'),
            'service_type': join_data.get('service_type', 'general')
        }
        
        token_response = call_token_service(token_request)
        
        if not token_response:
            return jsonify({'error': 'Failed to generate token'}), 500
        
        # Step 4: Create queue assignment record
        assignment_data = {
            'user_id': user_id,
            'queue_id': queue_id,
            'token_id': token_response['token_id'],
            'user_name': user_data.get('name'),
            'queue_name': queue_data.get('name'),
            'token_number': token_response['token_number'],
            'status': 'waiting',
            'joined_at': datetime.utcnow(),
            'estimated_wait_time': queue_data.get('average_wait_time', 10)
        }
        
        # Insert assignment record
        assignment_result = queue_assignments_collection.insert_one(assignment_data)
        
        # Update queue current count
        queues_collection.update_one(
            {'_id': queue_object_id},
            {
                '$inc': {'current_count': 1},
                '$set': {'updated_at': datetime.utcnow()}
            }
        )
        
        # Prepare response
        response_data = {
            'assignment_id': str(assignment_result.inserted_id),
            'user': {
                'id': user_id,
                'name': user_data.get('name'),
                'email': user_data.get('email')
            },
            'queue': {
                'id': queue_id,
                'name': queue_data.get('name'),
                'description': queue_data.get('description')
            },
            'token': {
                'id': token_response['token_id'],
                'number': token_response['token_number'],
                'status': token_response['status']
            },
            'assignment_details': {
                'status': 'waiting',
                'joined_at': assignment_data['joined_at'].isoformat(),
                'estimated_wait_time': assignment_data['estimated_wait_time']
            }
        }
        
        logger.info(f"User {user_id} successfully joined queue {queue_id} with token {token_response['token_id']}")
        return jsonify(response_data), 201
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Service communication error: {e}")
        return jsonify({'error': 'Service communication failed'}), 503
    except Exception as e:
        logger.error(f"Error joining queue: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/queues/assignments/<assignment_id>', methods=['GET'])
def get_assignment(assignment_id):
    """
    Get queue assignment details
    GET /api/queues/assignments/{assignment_id}
    Response: Assignment details with current status
    """
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(assignment_id)
        except InvalidId:
            return jsonify({'error': 'Invalid assignment ID format'}), 400
        
        # Query database for assignment
        assignment = queue_assignments_collection.find_one({'_id': object_id})
        
        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404
        
        # Format response
        assignment['_id'] = str(assignment['_id'])
        assignment['joined_at'] = assignment['joined_at'].isoformat()
        
        logger.info(f"Assignment retrieved: {assignment_id}")
        return jsonify(assignment), 200
        
    except Exception as e:
        logger.error(f"Error retrieving assignment {assignment_id}: {e}")
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
    # Get port from environment variable or default to 5002
    port = int(os.environ.get('PORT', 5002))
    
    logger.info(f"Starting Queue Service on port {port}")
    logger.info(f"User Service URL: {USER_SERVICE_URL}")
    logger.info(f"Token Service URL: {TOKEN_SERVICE_URL}")
    logger.info("Database connection established")
    logger.info("Ready to serve requests")
    
    # Run the Flask application
    app.run(host='0.0.0.0', port=port, debug=False)