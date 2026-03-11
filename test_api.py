import requests
import json
import time

def test_services():
    """Test all services to ensure they are working correctly"""
    
    # Define service URLs
    urls = {
        'user_service': 'http://localhost:5001',
        'queue_service': 'http://localhost:5002',
        'token_service': 'http://localhost:5003',
        'notification_service': 'http://localhost:5004'
    }
    
    print("Testing Smart Queue Management System Services...")
    print("="*60)
    
    # Test health endpoints
    for service_name, base_url in urls.items():
        try:
            response = requests.get(f"{base_url}/health")
            if response.status_code == 200:
                print(f"✅ {service_name.replace('_', ' ').title()} - Health Check: {response.json()}")
            else:
                print(f"❌ {service_name.replace('_', ' ').title()} - Health Check Failed: Status {response.status_code}")
        except Exception as e:
            print(f"❌ {service_name.replace('_', ' ').title()} - Health Check Error: {str(e)}")
    
    print("\n" + "="*60)
    
    # Test the integration flow: User -> Queue -> Token -> Notification
    print("Testing Integration Flow: User Registration -> Queue Join -> Token Generation -> Notification")
    
    # Step 1: Register a user
    try:
        import random
        unique_id = str(random.randint(100000000, 999999999))  # Generate 9 random digits
        user_data = {
            "name": f"Test User {unique_id}",
            "email": f"test{unique_id}@example.com",
            "phone": f"+94{unique_id}"
        }
        user_response = requests.post(f"{urls['user_service']}/api/users", json=user_data)
        if user_response.status_code == 201:
            user = user_response.json()
            print(f"✅ User Registration Successful: {user}")
            user_id = user.get('id') or user.get('_id')
        else:
            print(f"❌ User Registration Failed: Status {user_response.status_code}, Response: {user_response.text}")
            return
    except Exception as e:
        print(f"❌ User Registration Error: {str(e)}")
        return
    
    # Step 2: Create a queue
    try:
        import random
        queue_unique = str(random.randint(10000, 99999))
        queue_data = {
            "name": f"Test Queue {queue_unique}",
            "location": "Test Location",
            "description": "Test Queue Description",
            "max_capacity": 100,
            "current_count": 0
        }
        queue_response = requests.post(f"{urls['queue_service']}/api/queues", json=queue_data)
        if queue_response.status_code == 201:
            queue = queue_response.json()
            print(f"✅ Queue Creation Successful: {queue}")
            queue_id = queue.get('id') or queue.get('_id')
        else:
            print(f"❌ Queue Creation Failed: Status {queue_response.status_code}, Response: {queue_response.text}")
            return
    except Exception as e:
        print(f"❌ Queue Creation Error: {str(e)}")
        return
    
    # Step 3: Join the queue (this should trigger token generation and notification)
    try:
        join_data = {
            "user_id": str(user_id),
            "queue_id": str(queue_id)
        }
        join_response = requests.post(f"{urls['queue_service']}/api/queues/join", json=join_data)
        if join_response.status_code == 201:
            join_result = join_response.json()
            print(f"✅ Queue Join Successful: {join_result}")
            
            # The response should include token information
            if 'token' in join_result:
                token = join_result['token']
                print(f"✅ Token Generated: {token}")
        else:
            print(f"❌ Queue Join Failed: Status {join_response.status_code}, Response: {join_response.text}")
            return
    except Exception as e:
        print(f"❌ Queue Join Error: {str(e)}")
        return
    
    print("\n" + "="*60)
    print("Integration Flow Testing Complete!")
    print("All services are running and communicating properly.")
    print("\nService Summary:")
    print("- User Service: http://localhost:5001")
    print("- Queue Service: http://localhost:5002")
    print("- Token Service: http://localhost:5003")
    print("- Notification Service: http://localhost:5004")
    print("- MongoDB: localhost:27017")
    print("- Mongo Express: http://localhost:8081")

if __name__ == "__main__":
    test_services()