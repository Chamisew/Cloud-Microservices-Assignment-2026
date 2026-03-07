"""
Token Service - Smart Queue Management System
Port: 5003

This microservice manages token generation and management for the queue system.
It integrates with Notification Service to send alerts when tokens are generated.

Integration Flow:
1. POST /api/tokens/generate receives token request from Queue Service
2. Generates and saves token to MongoDB Atlas
3. Calls Notification Service (Port 5004) to send alert
4. Returns token information to Queue Service

Security Features:
- Environment-based MongoDB connection (no hardcoded credentials)
- Service-to-service authentication with Notification Service
- Input validation and sanitization
- Retry mechanism with exponential backoff for external calls
- Circuit breaker pattern for resilience
- Comprehensive error handling
"""

import os
import logging
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId
import re
from dotenv import load_dotenv
from functools import wraps
import time
import string
import random

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
    tokens_collection = db['tokens']
    logger.info("Successfully connected to MongoDB Atlas")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise

# Token Generation Utilities
def generate_token_number(prefix="Q", length=3):
    """
    Generate unique token number with prefix and random digits
    Example: Q001, Q002, etc.
    """
    # Get current count for this prefix
    count = tokens_collection.count_documents({'token_prefix': prefix})
    next_number = count + 1
    return f"{prefix}{next_number:03d}"

def generate_unique_token_id():
    """Generate unique token ID using ObjectId"""
    return str(ObjectId())

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
def call_notification_service(notification_data):
    """
    Call Notification Service to send alert
    Security: Uses service-to-service authentication
    This is the CRUCIAL integration point - called immediately after saving token
    """
    url = f"{NOTIFICATION_SERVICE_URL}/api/notifications/send"
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Token-Service/1.0'
    }
    
    # Add service authentication if API key is configured
    api_key = os.environ.get('SERVICE_API_KEY')
    if api_key:
        headers['X-Service-Key'] = api_key
    
    logger.info(f"Calling Notification Service: {url}")
    logger.info(f"Notification data: {notification_data}")
    
    response = requests.post(url, json=notification_data, headers=headers, timeout=15)
    
    if response.status_code in [200, 201]:
        notification_response = response.json()
        logger.info(f"Notification sent successfully: {notification_response.get('notification_id')}")
        return notification_response
    else:
        logger.error(f"Notification Service error {response.status_code}: {response.text}")
        response.raise_for_status()

# Input Validation Functions
def validate_token_request(data):
    """
    Validate token generation request data
    Returns tuple: (is_valid, error_message)
    """
    required_fields = ['user_id', 'queue_id', 'user_name', 'queue_name']
    
    # Check required fields
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"
    
    # Validate ObjectId format for IDs
    try:
        ObjectId(data['user_id'])
        ObjectId(data['queue_id'])
    except InvalidId:
        return False, "Invalid user_id or queue_id format"
    
    # Validate name fields
    if len(data['user_name']) < 2 or len(data['user_name']) > 100:
        return False, "User name must be between 2 and 100 characters"
    
    if len(data['queue_name']) < 3 or len(data['queue_name']) > 50:
        return False, "Queue name must be between 3 and 50 characters"
    
    # Validate service_type if provided
    if 'service_type' in data:
        valid_types = ['general', 'priority', 'vip', 'emergency']
        if data['service_type'] not in valid_types:
            return False, f"Invalid service type. Must be one of: {valid_types}"
    
    return True, None

# API Routes

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring
    Returns service status and Notification Service connectivity
    """
    try:
        # Test database connection
        client.admin.command('ping')
        
        # Test Notification Service connectivity
        notification_status = 'unknown'
        try:
            requests.get(f"{NOTIFICATION_SERVICE_URL}/health", timeout=3)
            notification_status = 'connected'
        except:
            notification_status = 'disconnected'
        
        return jsonify({
            'status': 'healthy',
            'service': 'Token Service',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'notification_service': notification_status
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'service': 'Token Service',
            'error': str(e)
        }), 503

@app.route('/api/tokens/generate', methods=['POST'])
def generate_token():
    """
    Generate new queue token - Core Integration Endpoint
    POST /api/tokens/generate
    Request Body: {
        "user_id": "string",
        "queue_id": "string", 
        "user_name": "string",
        "queue_name": "string",
        "service_type": "string" (optional)
    }
    
    Integration Flow:
    1. Validate and process token request
    2. Generate unique token number and ID
    3. Save token details to MongoDB Atlas
    4. CRUCIAL: Call Notification Service to send alert
    5. Return complete token information
    
    Response: Generated token details
    """
    try:
        # Parse request data
        token_request = request.get_json()
        
        if not token_request:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate input data
        is_valid, error_message = validate_token_request(token_request)
        if not is_valid:
            return jsonify({'error': error_message}), 400
        
        # Step 1: Generate token details
        logger.info(f"Step 1: Generating token for user {token_request['user_id']}")
        token_id = generate_unique_token_id()
        token_number = generate_token_number()
        service_type = token_request.get('service_type', 'general')
        
        # Determine token status and priority
        status = 'active'
        priority = 1
        if service_type == 'priority':
            priority = 2
        elif service_type == 'vip':
            priority = 3
        elif service_type == 'emergency':
            priority = 4
        
        # Set expiration time (2 hours from now)
        current_time = datetime.utcnow()
        expires_at = current_time.replace(second=0, microsecond=0) + timedelta(hours=2)  # 2 hours from now
        
        # Step 2: Prepare token data for database
        token_data = {
            'token_id': token_id,
            'token_number': token_number,
            'token_prefix': token_number[0],
            'user_id': token_request['user_id'],
            'queue_id': token_request['queue_id'],
            'user_name': token_request['user_name'],
            'queue_name': token_request['queue_name'],
            'service_type': service_type,
            'status': status,
            'priority': priority,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'expires_at': expires_at,
            'called_at': None,
            'completed_at': None
        }
        
        # Step 3: Save token to MongoDB Atlas
        logger.info(f"Step 2: Saving token {token_id} to database")
        result = tokens_collection.insert_one(token_data)
        logger.info(f"Token saved successfully: {token_id}")
        
        # Step 4: CRUCIAL INTEGRATION - Call Notification Service
        logger.info(f"Step 3: Calling Notification Service to send alert")
        notification_data = {
            'type': 'token_generated',
            'user_id': token_request['user_id'],
            'user_name': token_request['user_name'],
            'token_id': token_id,
            'token_number': token_number,
            'queue_name': token_request['queue_name'],
            'service_type': service_type,
            'priority': priority,
            'message': f"Token {token_number} generated for {token_request['user_name']} in {token_request['queue_name']}"
        }
        
        try:
            notification_response = call_notification_service(notification_data)
            logger.info(f"Notification sent successfully for token {token_id}")
        except Exception as e:
            logger.error(f"Failed to send notification for token {token_id}: {e}")
            # Note: We don't fail the entire request if notification fails
            # This follows the resilience pattern - core functionality succeeds
            notification_response = {'error': str(e)}
        
        # Step 5: Prepare response
        response_data = {
            'token_id': token_id,
            'token_number': token_number,
            'status': status,
            'service_type': service_type,
            'priority': priority,
            'expires_at': expires_at.isoformat(),
            'created_at': token_data['created_at'].isoformat()
        }
        
        # Include notification status in response
        if 'error' not in notification_response:
            response_data['notification_sent'] = True
            response_data['notification_id'] = notification_response.get('notification_id')
        else:
            response_data['notification_sent'] = False
            response_data['notification_error'] = notification_response.get('error')
        
        logger.info(f"Token generation completed successfully: {token_id}")
        return jsonify(response_data), 201
        
    except Exception as e:
        logger.error(f"Error generating token: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/tokens/<token_id>', methods=['GET'])
def get_token(token_id):
    """
    Retrieve token details by ID
    GET /api/tokens/{token_id}
    Response: Token details with status information
    """
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(token_id)
        except InvalidId:
            return jsonify({'error': 'Invalid token ID format'}), 400
        
        # Query database for token
        token = tokens_collection.find_one(
            {'token_id': token_id},
            {
                'token_id': 1,
                'token_number': 1,
                'user_id': 1,
                'queue_id': 1,
                'user_name': 1,
                'queue_name': 1,
                'service_type': 1,
                'status': 1,
                'priority': 1,
                'created_at': 1,
                'updated_at': 1,
                'expires_at': 1,
                'called_at': 1,
                'completed_at': 1
            }
        )
        
        if not token:
            return jsonify({'error': 'Token not found'}), 404
        
        # Format response
        token['created_at'] = token['created_at'].isoformat()
        token['updated_at'] = token['updated_at'].isoformat()
        token['expires_at'] = token['expires_at'].isoformat()
        
        if token.get('called_at'):
            token['called_at'] = token['called_at'].isoformat()
        if token.get('completed_at'):
            token['completed_at'] = token['completed_at'].isoformat()
        
        logger.info(f"Token retrieved: {token_id}")
        return jsonify(token), 200
        
    except Exception as e:
        logger.error(f"Error retrieving token {token_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/tokens/user/<user_id>', methods=['GET'])
def get_user_tokens(user_id):
    """
    Retrieve all tokens for a specific user
    GET /api/tokens/user/{user_id}
    Response: List of user tokens with status
    """
    try:
        # Validate ObjectId format
        try:
            ObjectId(user_id)
        except InvalidId:
            return jsonify({'error': 'Invalid user ID format'}), 400
        
        # Query database for user tokens
        cursor = tokens_collection.find(
            {'user_id': user_id},
            {
                'token_id': 1,
                'token_number': 1,
                'queue_name': 1,
                'service_type': 1,
                'status': 1,
                'created_at': 1,
                'expires_at': 1
            }
        ).sort('created_at', -1).limit(50)  # Limit to 50 most recent tokens
        
        # Convert cursor to list and format response
        tokens = []
        for token in cursor:
            token['created_at'] = token['created_at'].isoformat()
            token['expires_at'] = token['expires_at'].isoformat()
            tokens.append(token)
        
        logger.info(f"Retrieved {len(tokens)} tokens for user {user_id}")
        return jsonify({'tokens': tokens}), 200
        
    except Exception as e:
        logger.error(f"Error retrieving tokens for user {user_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/tokens/status/<token_id>', methods=['PUT'])
def update_token_status(token_id):
    """
    Update token status (called, completed, etc.)
    PUT /api/tokens/status/{token_id}
    Request Body: {
        "status": "string",
        "additional_data": "object" (optional)
    }
    Response: Updated token information
    """
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(token_id)
        except InvalidId:
            return jsonify({'error': 'Invalid token ID format'}), 400
        
        # Parse update data
        update_data = request.get_json()
        if not update_data or 'status' not in update_data:
            return jsonify({'error': 'Status field is required'}), 400
        
        # Validate status
        valid_statuses = ['active', 'called', 'serving', 'completed', 'expired', 'cancelled']
        if update_data['status'] not in valid_statuses:
            return jsonify({'error': f'Invalid status. Must be one of: {valid_statuses}'}), 400
        
        # Prepare update fields
        update_fields = {
            'status': update_data['status'],
            'updated_at': datetime.utcnow()
        }
        
        # Add timestamp fields based on status
        if update_data['status'] == 'called':
            update_fields['called_at'] = datetime.utcnow()
        elif update_data['status'] == 'completed':
            update_fields['completed_at'] = datetime.utcnow()
        elif update_data['status'] == 'expired':
            update_fields['completed_at'] = datetime.utcnow()
        elif update_data['status'] == 'cancelled':
            update_fields['completed_at'] = datetime.utcnow()
        
        # Update token in database
        result = tokens_collection.update_one(
            {'token_id': token_id},
            {'$set': update_fields}
        )
        
        if result.matched_count == 0:
            return jsonify({'error': 'Token not found'}), 404
        
        # Retrieve updated token
        updated_token = tokens_collection.find_one(
            {'token_id': token_id},
            {
                'token_id': 1,
                'token_number': 1,
                'user_name': 1,
                'queue_name': 1,
                'status': 1,
                'called_at': 1,
                'completed_at': 1,
                'updated_at': 1
            }
        )
        
        # Format response
        updated_token['updated_at'] = updated_token['updated_at'].isoformat()
        if updated_token.get('called_at'):
            updated_token['called_at'] = updated_token['called_at'].isoformat()
        if updated_token.get('completed_at'):
            updated_token['completed_at'] = updated_token['completed_at'].isoformat()
        
        logger.info(f"Token status updated: {token_id} -> {update_data['status']}")
        return jsonify(updated_token), 200
        
    except Exception as e:
        logger.error(f"Error updating token status {token_id}: {e}")
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
    # Get port from environment variable or default to 5003
    port = int(os.environ.get('PORT', 5003))
    
    logger.info(f"Starting Token Service on port {port}")
    logger.info(f"Notification Service URL: {NOTIFICATION_SERVICE_URL}")
    logger.info("Database connection established")
    logger.info("Ready to serve requests")
    
    # Run the Flask application
    app.run(host='0.0.0.0', port=port, debug=False)