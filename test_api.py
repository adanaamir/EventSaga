import requests
import json
import time

BASE_URL = "http://localhost:5000/api"

def check_server():
    """Check if the server is running"""
    try:
        response = requests.get("http://localhost:5000/api/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def print_response(response):
    """Pretty print the response"""
    print(f"Status: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)

# Check if server is running
print("Checking if server is running...")
if not check_server():
    print("\n❌ ERROR: Flask server is not running!")
    print("\nPlease start the server first:")
    print("  python run.py")
    print("\nThen run this test script in a separate terminal.")
    exit(1)

print("✅ Server is running!\n")

# Test 1: Health Check
print("=" * 50)
print("Test 1: Health Check")
print("=" * 50)
try:
    response = requests.get("http://localhost:5000/api/health")
    print_response(response)
    print()
except Exception as e:
    print(f"❌ Error: {e}\n")

# Test 2: Signup
print("=" * 50)
print("Test 2: User Signup")
print("=" * 50)

# Generate unique email to avoid duplicates
timestamp = int(time.time())
signup_data = {
    "email": f"testuser{timestamp}@gmail.com",
    "password": "Test123!@#",
    "name": "Test User",
    "role": "attendee"
}

print(f"Signing up with email: {signup_data['email']}")

try:
    response = requests.post(f"{BASE_URL}/auth/signup", json=signup_data)
    print_response(response)
    
    if response.status_code == 201:
        print("\n✅ Signup successful!")
        data = response.json()
        token = data['data']['session']['access_token']
        user_id = data['data']['user']['id']
        print(f"Token: {token[:50]}...")
        print(f"User ID: {user_id}")
        
        # Test 3: Get Current User
        print("\n" + "=" * 50)
        print("Test 3: Get Current User (with token)")
        print("=" * 50)
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
        print_response(response)
        
        if response.status_code == 200:
            print("\n✅ Authentication working!")
        else:
            print("\n❌ Authentication failed!")
        
        # Test 4: Login
        print("\n" + "=" * 50)
        print("Test 4: Login with Same Credentials")
        print("=" * 50)
        
        login_data = {
            "email": signup_data['email'],
            "password": signup_data['password']
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print_response(response)
        
        if response.status_code == 200:
            print("\n✅ Login successful!")
        else:
            print("\n❌ Login failed!")
            
    else:
        print("\n❌ Signup failed!")
        
except requests.exceptions.ConnectionError:
    print("\n❌ ERROR: Cannot connect to server!")
    print("Make sure the Flask server is running: python run.py")
except Exception as e:
    print(f"\n❌ Unexpected error: {e}")

print("\n" + "=" * 50)
print("Tests completed!")
print("=" * 50)