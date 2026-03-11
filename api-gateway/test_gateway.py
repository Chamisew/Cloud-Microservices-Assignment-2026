"""
Test script for API Gateway
Tests all routes to verify proper routing to microservices
"""

import requests
import json

BASE_URL = "http://localhost:8080"

def test_health():
    """Test gateway health endpoint"""
    print("Testing Gateway Health...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.status_code == 200

def test_gateway_status():
    """Test gateway status endpoint"""
    print("\nTesting Gateway Status...")
    response = requests.get(f"{BASE_URL}/api/status")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.status_code == 200

def test_user_service_routing():
    """Test routing to User Service"""
    print("\nTesting User Service Routing...")
    # Create a user
    user_data = {
        "name": "Test User",
        "email": "test@example.com",
        "phone": "+94123456789"
    }
    response = requests.post(f"{BASE_URL}/api/users", json=user_data)
    print(f"Create User Status: {response.status_code}")
    if response.status_code == 201:
        print(json.dumps(response.json(), indent=2))
        return response.json().get('id')
    elif response.status_code == 409:
        print("User already exists, getting users...")
        response = requests.get(f"{BASE_URL}/api/users")
        print(f"Get Users Status: {response.status_code}")
        if response.status_code == 200:
            users = response.json().get('users', [])
            if users:
                return users[0].get('_id')
    return None

def test_queue_service_routing():
    """Test routing to Queue Service"""
    print("\nTesting Queue Service Routing...")
    # Create a queue
    queue_data = {
        "name": "Test Queue",
        "description": "Test queue for gateway verification",
        "max_capacity": 50
    }
    response = requests.post(f"{BASE_URL}/api/queues", json=queue_data)
    print(f"Create Queue Status: {response.status_code}")
    if response.status_code == 201:
        print(json.dumps(response.json(), indent=2))
        return response.json().get('id')
    elif response.status_code == 409:
        print("Queue already exists, getting queues...")
        response = requests.get(f"{BASE_URL}/api/queues")
        print(f"Get Queues Status: {response.status_code}")
        if response.status_code == 200:
            queues = response.json().get('queues', [])
            if queues:
                return queues[0].get('_id')
    return None

def test_token_service_routing(user_id, queue_id):
    """Test routing to Token Service"""
    print("\nTesting Token Service Routing...")
    if not user_id or not queue_id:
        print("Skipping - need user_id and queue_id")
        return None
    
    token_data = {
        "user_id": user_id,
        "queue_id": queue_id,
        "user_name": "Test User",
        "queue_name": "Test Queue"
    }
    response = requests.post(f"{BASE_URL}/api/tokens/generate", json=token_data)
    print(f"Generate Token Status: {response.status_code}")
    if response.status_code == 201:
        print(json.dumps(response.json(), indent=2))
        return response.json().get('token_id')
    return None

def test_notification_service_routing():
    """Test routing to Notification Service"""
    print("\nTesting Notification Service Routing...")
    response = requests.get(f"{BASE_URL}/api/notifications")
    print(f"Get Notifications Status: {response.status_code}")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))
    return response.status_code == 200

if __name__ == "__main__":
    print("=" * 60)
    print("API Gateway Test Suite")
    print("=" * 60)
    
    try:
        # Test basic endpoints
        test_health()
        test_gateway_status()
        
        # Test service routing
        user_id = test_user_service_routing()
        queue_id = test_queue_service_routing()
        token_id = test_token_service_routing(user_id, queue_id)
        test_notification_service_routing()
        
        print("\n" + "=" * 60)
        print("Gateway tests completed!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to API Gateway")
        print("Make sure the gateway is running on port 8080")
    except Exception as e:
        print(f"\nError during testing: {e}")
