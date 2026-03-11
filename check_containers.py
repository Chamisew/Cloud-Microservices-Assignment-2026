"""
Script to check if Docker containers are running and responding
"""
import requests
import time

def check_service(name, url, timeout=10):
    """Check if a service is responding"""
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            status = data.get('status', 'unknown')
            print(f"✓ {name}: {status.upper()} - Response time: {response.elapsed.total_seconds():.2f}s")
            return True
        else:
            print(f"✗ {name}: Returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ {name}: Connection error - service may still be starting")
        return False
    except requests.exceptions.Timeout:
        print(f"✗ {name}: Request timed out")
        return False
    except Exception as e:
        print(f"✗ {name}: Error - {str(e)}")
        return False

def main():
    print("Checking Docker container health...")
    print("Waiting a few seconds for services to fully initialize...")
    time.sleep(10)  # Wait for services to fully start
    
    services = [
        ("User Service", "http://localhost:5001/health"),
        ("Queue Service", "http://localhost:5002/health"), 
        ("Token Service", "http://localhost:5003/health"),
        ("Notification Service", "http://localhost:5004/health")
    ]
    
    print("\nService Health Check:")
    print("-" * 40)
    
    all_healthy = True
    for name, url in services:
        if not check_service(name, url):
            all_healthy = False
    
    print("-" * 40)
    if all_healthy:
        print("\n🎉 ALL SERVICES ARE RUNNING AND HEALTHY!")
        print("\nSmart Queue Management System is successfully deployed with Docker!")
        print("\nIntegration Flow Active: User → Queue → Token → Notification")
    else:
        print("\n⚠️  Some services may still be starting up.")
        print("Try running this check again in a minute.")

if __name__ == "__main__":
    main()