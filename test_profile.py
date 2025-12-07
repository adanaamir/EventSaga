import requests
import json

BASE_URL = "http://localhost:5000/api"

# First, login to get a token
print("=" * 50)
print("Logging in...")
print("=" * 50)

login_data = {
    "email": "testuser1765120735@gmail.com",
    "password": "Test123!@#"
}

response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
if response.status_code != 200:
    print("❌ Login failed! Run signup test first.")
    exit(1)

token = response.json()['data']['session']['access_token']
user_id = response.json()['data']['user']['id']
headers = {"Authorization": f"Bearer {token}"}

print(f"✅ Logged in successfully")
print(f"User ID: {user_id}\n")

# Test 1: Update Profile
print("=" * 50)
print("Test 1: Update Profile")
print("=" * 50)

update_data = {
    "name": "Updated Test User",
    "bio": "I love attending amazing events!",
    "location": "Karachi, Pakistan",
}

response = requests.put(f"{BASE_URL}/profile", json=update_data, headers=headers)
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))

if response.status_code == 200:
    print("\n✅ Profile updated successfully!")
else:
    print("\n❌ Profile update failed!")

# Test 2: Get Public Profile
print("\n" + "=" * 50)
print("Test 2: Get Public Profile (no auth required)")
print("=" * 50)

response = requests.get(f"{BASE_URL}/profile/{user_id}")
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))

if response.status_code == 200:
    print("\n✅ Public profile retrieved!")
else:
    print("\n❌ Failed to get profile!")

# Test 3: Update Role to Organizer
print("\n" + "=" * 50)
print("Test 3: Switch Role to Organizer")
print("=" * 50)

role_data = {"role": "organizer"}
response = requests.patch(f"{BASE_URL}/profile/role", json=role_data, headers=headers)
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))

if response.status_code == 200:
    print("\n✅ Role updated to organizer!")
else:
    print("\n❌ Role update failed!")

# Test 4: Verify role change
print("\n" + "=" * 50)
print("Test 4: Verify Role Change")
print("=" * 50)

response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
print(f"Status: {response.status_code}")
current_role = response.json()['data']['role']
print(f"Current role: {current_role}")

if current_role == "organizer":
    print("\n✅ All profile tests passed!")
else:
    print("\n⚠️ Role didn't update properly")

print("\n" + "=" * 50)
print("Profile tests completed!")
print("=" * 50)