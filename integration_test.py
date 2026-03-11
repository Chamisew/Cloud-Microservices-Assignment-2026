"""
Integration Test Script for Smart Queue Management System
Verifies that all 4 services are working correctly and can communicate with each other
"""

import requests
import time
import json
from datetime import datetime

# Service URLs
USER_SERVICE_URL = "http://localhost:5001"
QUEUE_SERVICE_URL = "http://localhost:5002"
TOKEN_SERVICE_URL = "http://localhost:5003"
NOTIFICATION_SERVICE_URL = "http://localhost:5004"

def test_health_checks():
    """Test health endpoints of all services"""
    print("Testing health checks for all services...")
    
    services = [
        ("User Service", f"{USER_SERVICE_URL}/health"),
        ("Queue Service", f"{QUEUE_SERVICE_URL}/health"),
        ("Token Service", f"{TOKEN_SERVICE_URL}/health"),
        ("Notification Service", f"{NOTIFICATION_SERVICE_URL}/health")
    ]
    
    all_healthy = True
    for service_name, url in services:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                print(f"✓ {service_name}: {status.upper()}")
            else:
                print(f"✗ {service_name}: FAILED (HTTP {response.status_code})")
                all_healthy = False
        except Exception as e:
            print(f"✗ {service_name}: ERROR - {str(e)}")
            all_healthy = False
    
    return all_healthy

def test_user_service():
    """Test User Service functionality"""
    print("\nTesting User Service...")
    
    # Create a test user
    user_data = {
        "name": f"Test User {int(time.time())}",
        "email": f"test{int(time.time())}@example.com",
        "phone": "+94771234567",
        "nic": "123456789V"
    }
    
    try:
        response = requests.post(f"{USER_SERVICE_URL}/api/users", 
                                json=user_data, 
                                timeout=10)
        if response.status_code == 201:
            user = response.json()
            print(f"✓ User created successfully: {user['id']}")
            return user['id']
        else:
            print(f"✗ Failed to create user: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"✗ Error creating user: {str(e)}")
        return None

def test_queue_service():
    """Test Queue Service functionality"""
    print("\nTesting Queue Service...")
    
    # Create a test queue
    queue_data = {
        "name": f"Test Queue {int(time.time())}",
        "description": "Test queue for integration testing",
        "max_capacity": 50
    }
    
    try:
        response = requests.post(f"{QUEUE_SERVICE_URL}/api/queues", 
                                json=queue_data, 
                                timeout=10)
        if response.status_code == 201:
            queue = response.json()
            print(f"✓ Queue created successfully: {queue['id']}")
            return queue['id']
        else:
            print(f"✗ Failed to create queue: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"✗ Error creating queue: {str(e)}")
        return None

def test_full_integration_flow(user_id, queue_id):
    """Test the complete integration flow: User → Queue → Token → Notification"""
    print(f"\nTesting full integration flow...")
    print(f"User ID: {user_id}")
    print(f"Queue ID: {queue_id}")
    
    if not user_id or not queue_id:
        print("✗ Cannot test integration flow - missing user or queue ID")
        return False
    
    try:
        # Step 1: Join user to queue (this triggers the integration chain)
        join_data = {
            "user_id": user_id,
            "queue_id": queue_id,
            "service_type": "priority"
        }
        
        print("Step 1: Joining user to queue (calling Queue Service)...")
        response = requests.post(f"{QUEUE_SERVICE_URL}/api/queues/join", 
                                json=join_data, 
                                timeout=15)
        
        if response.status_code != 201:
            print(f"✗ Failed to join queue: {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        assignment_data = response.json()
        print(f"✓ User joined queue successfully")
        print(f"  Assignment ID: {assignment_data.get('assignment_id')}")
        print(f"  Token ID: {assignment_data['token'].get('id')}")
        print(f"  Token Number: {assignment_data['token'].get('number')}")
        
        token_id = assignment_data['token'].get('id')
        token_number = assignment_data['token'].get('number')
        
        # Step 2: Verify token was created in Token Service
        print(f"\nStep 2: Verifying token creation in Token Service...")
        response = requests.get(f"{TOKEN_SERVICE_URL}/api/tokens/{token_id}", timeout=10)
        if response.status_code == 200:
            token = response.json()
            print(f"✓ Token found in Token Service: {token['token_number']}")
        else:
            print(f"✗ Token not found in Token Service: {response.status_code}")
            return False
        
        # Step 3: Verify notification was created in Notification Service
        print(f"\nStep 3: Verifying notification creation in Notification Service...")
        # Get notifications to find the one created by the token service
        response = requests.get(f"{NOTIFICATION_SERVICE_URL}/api/notifications", 
                               params={"user_id": user_id}, timeout=10)
        if response.status_code == 200:
            notifications = response.json().get('notifications', [])
            matching_notifications = [n for n in notifications if n.get('token_number') == token_number]
            if matching_notifications:
                print(f"✓ Notification found in Notification Service: {matching_notifications[0].get('notification_id')}")
                print(f"  Message: {matching_notifications[0].get('message')}")
            else:
                print(f"✗ No matching notification found in Notification Service")
                print(f"  Looking for token number: {token_number}")
                print(f"  Available notifications: {len(notifications)}")
                return False
        else:
            print(f"✗ Failed to get notifications: {response.status_code}")
            return False
        
        print("\n✓ Full integration flow completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Error in integration flow: {str(e)}")
        return False

def main():
    print("="*60)
    print("Smart Queue Management System - Integration Test")
    print("="*60)
    
    # Wait a moment for services to be ready
    print("Waiting for services to be ready...")
    time.sleep(5)
    
    # Test health checks first
    if not test_health_checks():
        print("\n✗ Some services are not healthy. Please check the services.")
        return
    
    print("\n✓ All services are healthy!")
    
    # Test individual services
    user_id = test_user_service()
    queue_id = test_queue_service()
    
    if user_id and queue_id:
        # Test the complete integration flow
        success = test_full_integration_flow(user_id, queue_id)
        if success:
            print("\n🎉 ALL TESTS PASSED! Integration is working correctly.")
        else:
            print("\n❌ INTEGRATION TEST FAILED!")
    else:
        print("\n❌ Could not proceed with integration test - failed to create test data")
    
    print("\n" + "="*60)
    print("Test Summary:")
    print("- Health checks: Completed")
    print("- User Service: Tested")
    print("- Queue Service: Tested")
    print("- Integration Flow: Tested")
    print("="*60)

if __name__ == "__main__":
    main()