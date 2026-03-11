import requests
import json
import random

def test_cross_service_endpoints():
    """Test the new cross-service endpoints in the User Service"""
    
    print("Testing Cross-Service Endpoints in User Service...")
    print("="*60)
    
    # First, create a test user
    user_data = {
        "name": f"Test User Cross Service {random.randint(10000, 99999)}",
        "email": f"cross_test_{random.randint(10000, 99999)}@example.com",
        "phone": f"+94{random.randint(100000000, 999999999)}"
    }
    
    try:
        user_response = requests.post("http://localhost:5001/api/users", json=user_data)
        if user_response.status_code == 201:
            user = user_response.json()
            user_id = user['id']
            print(f"✅ User created: {user['name']} (ID: {user_id})")
        else:
            print(f"❌ User creation failed: {user_response.status_code} - {user_response.text}")
            return
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        return
    
    # Create a test queue
    queue_data = {
        "name": f"Cross Service Test Queue {random.randint(1000, 9999)}",
        "location": "Test Location",
        "description": "Test Queue for Cross Service Operations",
        "max_capacity": 50,
        "current_count": 0
    }
    
    try:
        queue_response = requests.post("http://localhost:5002/api/queues", json=queue_data)
        if queue_response.status_code == 201:
            queue = queue_response.json()
            queue_id = queue['id']
            print(f"✅ Queue created: {queue['name']} (ID: {queue_id})")
        else:
            print(f"❌ Queue creation failed: {queue_response.status_code} - {queue_response.text}")
            return
    except Exception as e:
        print(f"❌ Error creating queue: {e}")
        return
    
    # Test the new User Service endpoint: join-queue
    print("\nTesting User Service -> Queue Service integration...")
    join_data = {
        "queue_id": queue_id,
        "service_type": "general"
    }
    
    try:
        join_response = requests.post(f"http://localhost:5001/api/users/{user_id}/join-queue", json=join_data)
        if join_response.status_code == 201:
            result = join_response.json()
            print(f"✅ Cross-service queue join successful: {result['message']}")
            print(f"   Assignment ID: {result['queue_assignment']['assignment_id']}")
            print(f"   Token Number: {result['queue_assignment']['token']['number']}")
        else:
            print(f"❌ Cross-service queue join failed: {join_response.status_code} - {join_response.text}")
    except Exception as e:
        print(f"❌ Error in cross-service queue join: {e}")
    
    # Test the new User Service endpoint: generate-token
    print("\nTesting User Service -> Token Service integration...")
    token_data = {
        "queue_id": queue_id,
        "queue_name": queue['name'],
        "service_type": "priority"
    }
    
    try:
        token_response = requests.post(f"http://localhost:5001/api/users/{user_id}/generate-token", json=token_data)
        if token_response.status_code == 201:
            result = token_response.json()
            print(f"✅ Cross-service token generation successful: {result['message']}")
            print(f"   Token ID: {result['token']['token_id']}")
            print(f"   Token Number: {result['token']['token_number']}")
        else:
            print(f"❌ Cross-service token generation failed: {token_response.status_code} - {token_response.text}")
    except Exception as e:
        print(f"❌ Error in cross-service token generation: {e}")
    
    print("\n" + "="*60)
    print("Cross-Service Testing Complete!")

if __name__ == "__main__":
    test_cross_service_endpoints()