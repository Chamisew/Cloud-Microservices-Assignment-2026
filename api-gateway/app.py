"""
API Gateway - Smart Queue Management System
Port: 8080

Central entry point for all client requests. Routes traffic to microservices:
- /api/users/*      -> User Service (5001)
- /api/queues/*     -> Queue Service (5002)
- /api/tokens/*     -> Token Service (5003)
- /api/notifications/* -> Notification Service (5004)
"""

import os
import logging
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import time

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Service Configuration
SERVICES = {
    'user': {
        'name': 'User Service',
        'url': os.environ.get('USER_SERVICE_URL', 'http://user-service:5001'),
        'prefix': '/api/users'
    },
    'queue': {
        'name': 'Queue Service',
        'url': os.environ.get('QUEUE_SERVICE_URL', 'http://queue-service:5002'),
        'prefix': '/api/queues'
    },
    'token': {
        'name': 'Token Service',
        'url': os.environ.get('TOKEN_SERVICE_URL', 'http://token-service:5003'),
        'prefix': '/api/tokens'
    },
    'notification': {
        'name': 'Notification Service',
        'url': os.environ.get('NOTIFICATION_SERVICE_URL', 'http://notification-service:5004'),
        'prefix': '/api/notifications'
    }
}

REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', 30))


def get_service_for_path(path):
    """Determine which service should handle the given path"""
    path = path.lower()
    if path.startswith('/api/users'):
        return 'user'
    elif path.startswith('/api/queues'):
        return 'queue'
    elif path.startswith('/api/tokens'):
        return 'token'
    elif path.startswith('/api/notifications'):
        return 'notification'
    return None


def forward_request(service_key, path, method, headers=None, data=None, params=None):
    """Forward request to the appropriate microservice"""
    service = SERVICES.get(service_key)
    if not service:
        logger.error(f"Service not found for key: {service_key}")
        return {'error': 'Service not found'}, 404, {}
    
    service_url = service.get('url')
    if not service_url:
        logger.error(f"Service URL not configured for: {service_key}")
        return {'error': f'Service URL not configured for {service_key}'}, 500, {}
    
    target_url = f"{service_url}{path}"
    logger.info(f"Target URL: {target_url}")
    
    forward_headers = {}
    if headers:
        for key, value in headers.items():
            # Skip problematic headers that can cause issues
            key_lower = key.lower()
            if key_lower not in ['host', 'content-length', 'connection', 'keep-alive', 
                                 'content-type', 'accept-encoding', 'transfer-encoding']:
                forward_headers[key] = value
    
    # Ensure Accept header is set for JSON responses
    forward_headers['Accept'] = 'application/json'
    
    # Set Content-Type only for methods that have a body
    if method in ['POST', 'PUT', 'PATCH'] and data:
        forward_headers['Content-Type'] = 'application/json'
    
    forward_headers['X-Forwarded-By'] = 'API-Gateway'
    forward_headers['X-Forwarded-For'] = request.remote_addr
    
    try:
        logger.info(f"Forwarding {method} {path} to {service['name']} at {target_url}")
        logger.info(f"Forward headers: {forward_headers}")
        start_time = time.time()
        
        response = requests.request(
            method=method,
            url=target_url,
            headers=forward_headers,
            json=data if data else None,
            params=params if params else None,
            timeout=REQUEST_TIMEOUT
        )
        
        duration = time.time() - start_time
        logger.info(f"Response from {service['name']}: {response.status_code} in {duration:.3f}s")
        
        try:
            response_data = response.json()
        except ValueError:
            response_data = response.text
        
        response_headers = {
            'X-Service-Name': service['name'],
            'X-Response-Time': f"{duration:.3f}s"
        }
        
        return response_data, response.status_code, response_headers
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout calling {service['name']}")
        return {'error': f'{service["name"]} timeout'}, 504, {}
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error calling {service['name']}")
        return {'error': f'{service["name"]} unavailable'}, 503, {}
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling {service['name']}: {e}")
        return {'error': f'Service communication failed'}, 502, {}


@app.route('/health', methods=['GET'])
def health_check():
    """Health check for gateway - lightweight for Docker health checks"""
    return jsonify({
        'status': 'healthy',
        'service': 'API Gateway',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@app.route('/api/status', methods=['GET'])
def gateway_status():
    """Detailed status check including backend services and routing information"""
    services_health = {}
    all_healthy = True
    
    for key, config in SERVICES.items():
        try:
            # Add /health to the service URL
            health_url = f"{config['url']}/health"
            response = requests.get(health_url, timeout=5)
            services_health[key] = {
                'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                'name': config['name'],
                'target': config['url']
            }
            if response.status_code != 200:
                all_healthy = False
        except Exception as e:
            services_health[key] = {
                'status': 'unreachable',
                'name': config['name'],
                'target': config['url'],
                'error': str(e)
            }
            all_healthy = False
    
    return jsonify({
        'status': 'healthy' if all_healthy else 'degraded',
        'service': 'API Gateway',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat(),
        'services': services_health,
        'routes': {
            'users': {'path': '/api/users/*', 'target': SERVICES['user']['url']},
            'queues': {'path': '/api/queues/*', 'target': SERVICES['queue']['url']},
            'tokens': {'path': '/api/tokens/*', 'target': SERVICES['token']['url']},
            'notifications': {'path': '/api/notifications/*', 'target': SERVICES['notification']['url']}
        }
    }), 200


@app.route('/api/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def api_gateway(path):
    """Main gateway route handler"""
    full_path = f"/api/{path}"
    service_key = get_service_for_path(full_path)
    
    if not service_key:
        logger.warning(f"Unknown API endpoint: {full_path}")
        return jsonify({'error': 'Unknown API endpoint'}), 404
    
    # Skip logging for health checks to reduce noise
    if full_path != '/health':
        logger.info(f"Routing {request.method} {full_path} to {service_key} service")
    
    response_data, status_code, headers = forward_request(
        service_key=service_key,
        path=full_path,
        method=request.method,
        headers=dict(request.headers),
        data=(request.get_json(silent=True) if (
            request.method in ['POST', 'PUT', 'PATCH'] and
            request.content_length is not None and
            request.content_length > 0
        ) else None),
        params=request.args
    )
    
    if full_path != '/health':
        logger.info(f"Response for {full_path}: {status_code}")
    
    response = jsonify(response_data)
    response.status_code = status_code
    for key, value in headers.items():
        response.headers[key] = value
    
    return response


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting API Gateway on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
