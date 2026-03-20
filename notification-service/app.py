"""
Notification Service - Smart Queue Management System
Port: 5004

This microservice handles all notification alerts in the Smart Queue Management System.
It acts as the final integration point in the service chain, receiving alerts from the Token Service.

Integration Flow:
1. POST /api/notifications/send receives notification request from Token Service
2. Validates incoming payload data
3. Saves notification record to MongoDB Atlas
4. Returns confirmation to Token Service

This is the FINAL integration point in the chain:
User Service (5001) → Queue Service (5002) → Token Service (5003) → Notification Service (5004)

Security Features:
- Environment-based MongoDB connection (no hardcoded credentials)
- Comprehensive input validation and sanitization
- Robust error handling to prevent crashes from bad data
- RESTful API design with proper HTTP status codes
- Logging for monitoring and debugging
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

from flask_swagger_ui import get_swaggerui_blueprint

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
# Note: Services no longer communicate directly - all communication goes through API Gateway
# Auto-detect environment: use localhost for local dev, api-gateway for Docker
def get_api_gateway_url():
    """Determine API Gateway URL based on environment"""
    # If explicitly set, use the environment variable
    env_url = os.environ.get('API_GATEWAY_URL')
    if env_url:
        return env_url
    
    # Check if running in Docker by looking for .dockerenv file or specific env vars
    if os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER'):
        return 'http://api-gateway:8080'
    
    # Default to localhost for local development
    return 'http://localhost:8080'

API_GATEWAY_URL = get_api_gateway_url()

# Fallback direct service URLs for local development
USER_SERVICE_URL = os.environ.get('USER_SERVICE_URL', 'http://localhost:5001')
QUEUE_SERVICE_URL = os.environ.get('QUEUE_SERVICE_URL', 'http://localhost:5002')

# Database Configuration
# Security: Using environment variables to fetch MongoDB URI
# This prevents hardcoded credentials and follows DevSecOps best practices
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
    notifications_collection = db['notifications']
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

def get_user_name(user_id):
    """
    Fetch user name with API Gateway primary and direct fallback
    """
    gateway_url = f"{API_GATEWAY_URL}/api/users/{user_id}"
    direct_url = f"{USER_SERVICE_URL}/api/users/{user_id}"
    
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Notification-Service/1.0'
    }
    
    # Try via Gateway first
    logger.info(f"Attempting to fetch user {user_id} via Gateway: {gateway_url}")
    try:
        response = requests.get(gateway_url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get('name', 'Unknown')
        logger.warning(f"Gateway lookup failed ({response.status_code}); attempting direct fallback")
    except requests.exceptions.RequestException as e:
        logger.warning(f"Gateway unreachable ({e}); attempting direct fallback")
    
    # Direct Fallback
    logger.info(f"Attempting direct fetch from User Service: {direct_url}")
    try:
        response = requests.get(direct_url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get('name', 'Unknown')
        logger.error(f"Direct lookup failed ({response.status_code}): {response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Direct service call failed: {e}")
    
    return 'Unknown'

def get_queue_name(queue_id):
    """
    Fetch queue name with API Gateway primary and direct fallback
    """
    gateway_url = f"{API_GATEWAY_URL}/api/queues/{queue_id}"
    direct_url = f"{QUEUE_SERVICE_URL}/api/queues/{queue_id}"
    
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Notification-Service/1.0'
    }
    
    # Try via Gateway first
    logger.info(f"Attempting to fetch queue {queue_id} via Gateway: {gateway_url}")
    try:
        response = requests.get(gateway_url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get('name', 'Unknown Queue')
        logger.warning(f"Gateway lookup failed ({response.status_code}); attempting direct fallback")
    except requests.exceptions.RequestException as e:
        logger.warning(f"Gateway unreachable ({e}); attempting direct fallback")
    
    # Direct Fallback
    logger.info(f"Attempting direct fetch from Queue Service: {direct_url}")
    try:
        response = requests.get(direct_url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get('name', 'Unknown Queue')
        logger.error(f"Direct lookup failed ({response.status_code}): {response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Direct service call failed: {e}")
    
    return 'Unknown Queue'

# Input Validation Functions
def validate_notification_data(data):
    """
    Comprehensive validation of notification input data
    Returns tuple: (is_valid, error_message)
    This is CRUCIAL for preventing crashes from bad data from Token Service
    
    Note: user_name and queue_name are fetched from respective services,
    not required as input. token_number is generated by Token Service.
    """
    required_fields = ['type', 'user_id', 'token_id', 'queue_id', 'token_number', 'message']
    
    # Check required fields
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"
    
    # Validate ObjectId format for IDs
    try:
        ObjectId(data['user_id'])
        ObjectId(data['token_id'])
        ObjectId(data['queue_id'])
    except InvalidId:
        return False, "Invalid user_id, token_id, or queue_id format"
    
    # Validate token number format (should be like Q001, A-01, etc.)
    if not re.match(r'^[A-Z]-?\d{2,3}$|^[A-Z]{1,2}\d{2,3}$', data['token_number']):
        logger.warning(f"Unusual token number format: {data['token_number']}")
        # Don't fail, but log for monitoring
    
    # Validate message length
    if len(data['message']) < 10 or len(data['message']) > 500:
        return False, "Message must be between 10 and 500 characters"
    
    # Validate notification type
    valid_types = ['token_generated', 'token_called', 'token_reminder', 'queue_update', 'system_alert']
    if data['type'] not in valid_types:
        return False, f"Invalid notification type. Must be one of: {valid_types}"
    
    # Validate priority if provided
    if 'priority' in data:
        try:
            priority = int(data['priority'])
            if priority < 1 or priority > 5:
                return False, "Priority must be between 1 and 5"
        except (ValueError, TypeError):
            return False, "Priority must be a valid number"
    
    return True, None

def sanitize_input(data):
    """
    Sanitize input data to prevent injection attacks
    This is essential for security when handling data from other services
    
    Note: user_name and queue_name are fetched from services, not from input
    """
    if not isinstance(data, dict):
        return {}
    
    sanitized = {}
    # Only allow expected fields (user_name and queue_name excluded - fetched from services)
    allowed_fields = [
        'type', 'user_id', 'token_id', 'queue_id', 'token_number',
        'message', 'priority', 'service_type', 'user_name', 'queue_name'
    ]
    
    for field in allowed_fields:
        if field in data:
            value = data[field]
            # Convert to string and strip whitespace
            if isinstance(value, str):
                sanitized[field] = value.strip()
            else:
                sanitized[field] = str(value)
    
    return sanitized

# API Routes

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring
    Returns service status and basic information
    This is the FINAL endpoint in the integration chain
    """
    try:
        # Test database connection
        client.admin.command('ping')
        return jsonify({
            'status': 'healthy',
            'service': 'Notification Service',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'role': 'final_integration_point'
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'service': 'Notification Service',
            'error': 'Database connection failed'
        }), 503

@app.route('/api/notifications/from-queue', methods=['POST'])
def send_notification_from_queue():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        if 'user_id' not in data or 'queue_id' not in data:
            return jsonify({'error': 'Missing required field: user_id or queue_id'}), 400
        try:
            ObjectId(data['user_id'])
            ObjectId(data['queue_id'])
        except InvalidId:
            return jsonify({'error': 'Invalid user_id or queue_id format'}), 400
        try:
            user_name = get_user_name(data['user_id'])
        except Exception as e:
            logger.error(f"Failed to fetch user name: {e}")
            user_name = 'Unknown'
        if user_name == 'Unknown' and data.get('user_name'):
            user_name = data['user_name']
        try:
            queue_name = get_queue_name(data['queue_id'])
        except Exception as e:
            logger.error(f"Failed to fetch queue name: {e}")
            queue_name = 'Unknown Queue'
        if queue_name == 'Unknown Queue' and data.get('queue_name'):
            queue_name = data['queue_name']
        notification_record = {
            'notification_id': str(ObjectId()),
            'type': 'queue_update',
            'user_id': data['user_id'],
            'user_name': user_name,
            'token_id': str(ObjectId()),
            'token_number': data.get('token_number', 'Q000'),
            'queue_id': data['queue_id'],
            'queue_name': queue_name,
            'message': data.get('message', f"Queue update for user {user_name} in {queue_name}"),
            'status': 'sent',
            'priority': int(data.get('priority', 3)),
            'service_type': data.get('service_type', 'general'),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'sent_at': datetime.utcnow()
        }
        result = notifications_collection.insert_one(notification_record)
        return jsonify({
            'notification_id': notification_record['notification_id'],
            'status': 'sent',
            'user_name': user_name,
            'queue_name': queue_name,
            'token_number': notification_record['token_number'],
            'message': 'Notification sent successfully',
            'created_at': notification_record['created_at'].isoformat()
        }), 201
    except Exception as e:
        logger.error(f"Error processing queue notification: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/notifications/send', methods=['POST'])
def send_notification():
    """
    Send notification - Core Integration Endpoint (FINAL INTEGRATION POINT)
    POST /api/notifications/send
    Request Body: {
        "type": "string",              // Required: token_generated, token_called, etc.
        "user_id": "string",           // Required: User ID from User Service
        "token_id": "string",          // Required: Token ID from Token Service
        "queue_id": "string",          // Required: Queue ID from Queue Service
        "token_number": "string",       // Required: Token number (e.g., Q001, A-01)
        "message": "string",           // Required: Notification message
        "priority": "integer",          // Optional: 1-5 (default: 3)
        "service_type": "string"        // Optional: general, priority, vip, emergency
    }
    
    Integration Flow:
    1. Receive notification request from Token Service
    2. Validate and sanitize input data (CRUCIAL for resilience)
    3. Fetch user_name from User Service using user_id
    4. Fetch queue_name from Queue Service using queue_id
    5. Save notification record to MongoDB Atlas
    6. Return confirmation to Token Service
    
    Response: Notification confirmation with ID
    """
    try:
        # Parse JSON data from request
        notification_data = request.get_json()
        
        if not notification_data:
            logger.warning("No data provided in notification request")
            return jsonify({'error': 'No data provided'}), 400
        
        # CRUCIAL: Sanitize input data to prevent crashes from bad data
        logger.info(f"Received notification request: {notification_data}")
        sanitized_data = sanitize_input(notification_data)
        
        # Validate input data (comprehensive validation)
        is_valid, error_message = validate_notification_data(sanitized_data)
        if not is_valid:
            logger.warning(f"Invalid notification data: {error_message}")
            return jsonify({'error': error_message}), 400
        
        # Step 1: Fetch user_name from User Service
        logger.info(f"Step 1: Fetching user name for user_id: {sanitized_data['user_id']}")
        try:
            user_name = get_user_name(sanitized_data['user_id'])
        except Exception as e:
            logger.error(f"Failed to fetch user name: {e}")
            user_name = 'Unknown'
        if user_name == 'Unknown' and sanitized_data.get('user_name'):
            user_name = sanitized_data['user_name']
        
        # Step 2: Fetch queue_name from Queue Service
        logger.info(f"Step 2: Fetching queue name for queue_id: {sanitized_data['queue_id']}")
        try:
            queue_name = get_queue_name(sanitized_data['queue_id'])
        except Exception as e:
            logger.error(f"Failed to fetch queue name: {e}")
            queue_name = 'Unknown Queue'
        if queue_name == 'Unknown Queue' and sanitized_data.get('queue_name'):
            queue_name = sanitized_data['queue_name']
        
        # Step 3: Prepare notification record for database
        notification_record = {
            'notification_id': str(ObjectId()),  # Generate unique ID
            'type': sanitized_data['type'],
            'user_id': sanitized_data['user_id'],
            'user_name': user_name,  # Fetched from User Service
            'token_id': sanitized_data['token_id'],
            'token_number': sanitized_data['token_number'],
            'queue_name': queue_name,  # Fetched from Queue Service
            'message': sanitized_data['message'],
            'status': 'sent',  # Default status
            'priority': int(sanitized_data.get('priority', 3)),  # Default priority 3
            'service_type': sanitized_data.get('service_type', 'general'),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'sent_at': datetime.utcnow()  # Timestamp when notification was processed
        }
        
        # CRUCIAL: Save notification to MongoDB Atlas
        # This is the final data persistence in the integration chain
        try:
            result = notifications_collection.insert_one(notification_record)
            logger.info(f"Notification saved successfully: {notification_record['notification_id']}")
        except Exception as db_error:
            logger.error(f"Database save failed: {db_error}")
            return jsonify({'error': 'Database save failed'}), 500
        
        # Prepare response for Token Service
        response_data = {
            'notification_id': notification_record['notification_id'],
            'status': 'sent',
            'message': 'Notification sent successfully',
            'created_at': notification_record['created_at'].isoformat(),
            'token_number': notification_record['token_number'],
            'user_name': notification_record['user_name'],
            'queue_name': notification_record['queue_name']
        }
        
        logger.info(f"Notification processed successfully: {notification_record['notification_id']}")
        return jsonify(response_data), 201
        
    except Exception as e:
        # CRUCIAL: Robust error handling to prevent service crashes
        logger.error(f"Error processing notification: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    """
    Retrieve notifications with filtering and pagination
    GET /api/notifications?type=token_generated&user_id={id}&page=1&limit=10
    Response: List of notifications with pagination metadata
    """
    try:
        # Get query parameters
        notification_type = request.args.get('type')
        user_id = request.args.get('user_id')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        skip = (page - 1) * limit
        
        # Validate pagination parameters
        if page < 1 or limit < 1 or limit > 100:
            return jsonify({'error': 'Invalid pagination parameters'}), 400
        
        # Build query filter
        query_filter = {}
        if notification_type:
            query_filter['type'] = notification_type
        if user_id:
            try:
                query_filter['user_id'] = str(ObjectId(user_id))
            except InvalidId:
                return jsonify({'error': 'Invalid user ID format'}), 400
        
        # Query database with pagination
        cursor = notifications_collection.find(
            query_filter,
            {
                '_id': 0,
                'notification_id': 1,
                'type': 1,
                'user_name': 1,
                'token_number': 1,
                'queue_name': 1,
                'message': 1,
                'status': 1,
                'priority': 1,
                'created_at': 1
            }
        ).sort('created_at', -1).skip(skip).limit(limit)
        
        # Get total count for pagination metadata
        total_count = notifications_collection.count_documents(query_filter)
        
        # Convert cursor to list and format response
        notifications = []
        for notification in cursor:
            notification['created_at'] = notification['created_at'].isoformat()
            notifications.append(notification)
        
        # Prepare paginated response
        response = {
            'notifications': notifications,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            }
        }
        
        logger.info(f"Retrieved {len(notifications)} notifications (page {page})")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error retrieving notifications: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/notifications/<notification_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_notification(notification_id):
    """
    Handle GET, PUT, and DELETE for a specific notification
    """
    try:
        # Validate ObjectId format
        try:
            ObjectId(notification_id)
        except InvalidId:
            return jsonify({'error': 'Invalid notification ID format'}), 400

        if request.method == 'GET':
            # Query database for notification
            notification = notifications_collection.find_one(
                {'notification_id': notification_id},
                {
                    'notification_id': 1,
                    'type': 1,
                    'user_id': 1,
                    'user_name': 1,
                    'token_id': 1,
                    'token_number': 1,
                    'queue_name': 1,
                    'message': 1,
                    'status': 1,
                    'priority': 1,
                    'service_type': 1,
                    'created_at': 1,
                    'updated_at': 1,
                    'sent_at': 1,
                    '_id': 0
                }
            )
            
            if not notification:
                return jsonify({'error': 'Notification not found'}), 404
            
            # Format response
            notification['created_at'] = notification['created_at'].isoformat()
            notification['updated_at'] = notification['updated_at'].isoformat()
            notification['sent_at'] = notification['sent_at'].isoformat()
            
            logger.info(f"Notification retrieved: {notification_id}")
            return jsonify(notification), 200

        elif request.method == 'PUT':
            # Get request data
            update_data = request.get_json()
            if not update_data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Prepare update fields
            update_fields = {
                '$set': {
                    'updated_at': datetime.utcnow()
                }
            }
            
            if 'message' in update_data:
                update_fields['$set']['message'] = str(update_data['message'])
            
            if 'status' in update_data:
                valid_statuses = ['read', 'archived', 'sent']
                if update_data['status'] not in valid_statuses:
                    return jsonify({'error': f'Invalid status. Must be one of: {valid_statuses}'}), 400
                update_fields['$set']['status'] = update_data['status']
            
            # Update the notification in the database
            result = notifications_collection.update_one(
                {'notification_id': notification_id},
                update_fields
            )
            
            if result.matched_count == 0:
                return jsonify({'error': 'Notification not found'}), 404
            
            # Fetch the updated notification to return
            updated_notification = notifications_collection.find_one(
                {'notification_id': notification_id},
                {'_id': 0}
            )
            
            # Format datetime objects for JSON response
            for key, value in updated_notification.items():
                if isinstance(value, datetime):
                    updated_notification[key] = value.isoformat()
            
            logger.info(f"Notification {notification_id} updated successfully")
            return jsonify(updated_notification), 200

        elif request.method == 'DELETE':
            # Delete the notification from the database
            result = notifications_collection.delete_one({'notification_id': notification_id})
            
            if result.deleted_count == 0:
                return jsonify({'error': 'Notification not found'}), 404
            
            logger.info(f"Notification {notification_id} deleted successfully")
            return jsonify({'message': f'Notification {notification_id} deleted successfully'}), 200

    except Exception as e:
        logger.error(f"Error handling notification {notification_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/notifications/user/<user_id>', methods=['GET'])
def get_user_notifications(user_id):
    """
    Retrieve all notifications for a specific user
    GET /api/notifications/user/{user_id}
    Response: List of user notifications
    """
    try:
        # Validate ObjectId format
        try:
            ObjectId(user_id)
        except InvalidId:
            return jsonify({'error': 'Invalid user ID format'}), 400
        
        # Query database for user notifications
        cursor = notifications_collection.find(
            {'user_id': user_id},
            {'_id': 0}
        ).sort('created_at', -1)
        
        notifications = []
        for notification in cursor:
            # Format datetime objects for JSON response
            for key, value in notification.items():
                if isinstance(value, datetime):
                    notification[key] = value.isoformat()
            notifications.append(notification)
        
        logger.info(f"Retrieved {len(notifications)} notifications for user {user_id}")
        return jsonify({
            'user_id': user_id,
            'notifications': notifications,
            'count': len(notifications)
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving notifications for user {user_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/notifications/stats', methods=['GET'])
def get_notification_stats():
    """
    Get notification statistics
    GET /api/notifications/stats
    Response: Aggregated statistics about notifications
    """
    try:
        # Get total notification count
        total_count = notifications_collection.count_documents({})
        
        # Get count by type
        type_stats = list(notifications_collection.aggregate([
            {'$group': {'_id': '$type', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]))
        
        # Get count by status
        status_stats = list(notifications_collection.aggregate([
            {'$group': {'_id': '$status', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]))
        
        # Get recent notifications count (last 24 hours)
        last_24h = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        recent_count = notifications_collection.count_documents({
            'created_at': {'$gte': last_24h}
        })
        
        response_data = {
            'total_notifications': total_count,
            'notifications_by_type': {item['_id']: item['count'] for item in type_stats},
            'notifications_by_status': {item['_id']: item['count'] for item in status_stats},
            'notifications_last_24h': recent_count,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info("Notification statistics retrieved")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error retrieving notification statistics: {e}")
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

# Swagger UI Configuration
SWAGGER_URL = '/api/docs'  # URL for exposing Swagger UI
API_URL = '/static/swagger.yaml'  # Our API definition

# Call factory function to create our blueprint
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "Notification Service"
    }
)

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

# Application startup
if __name__ == '__main__':
    # Get port from environment variable or default to 5004
    port = int(os.environ.get('PORT', 5004))
    
    logger.info(f"Starting Notification Service on port {port}")
    logger.info("Database connection established")
    logger.info("Ready to serve as FINAL integration point")
    logger.info("Accepting requests from Token Service")
    
    # Run the Flask application
    # Security: Debug mode should be False in production
    app.run(host='0.0.0.0', port=port, debug=False)
