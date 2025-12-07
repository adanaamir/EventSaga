import requests
import json
import time

BASE_URL = "http://localhost:5000/api"

class TestRunner:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.passed = 0
        self.failed = 0
    
    def print_test(self, name):
        print("\n" + "=" * 60)
        print(f"TEST: {name}")
        print("=" * 60)
    
    def assert_status(self, response, expected_status, test_name):
        if response.status_code == expected_status:
            print(f"✅ {test_name} - Status: {response.status_code}")
            self.passed += 1
            return True
        else:
            print(f"❌ {test_name} - Expected {expected_status}, got {response.status_code}")
            print(json.dumps(response.json(), indent=2))
            self.failed += 1
            return False
    
    def print_summary(self):
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"Total: {self.passed + self.failed}")
        print("=" * 60)

runner = TestRunner()

# Test 1: Health Check
runner.print_test("Health Check")
response = requests.get(f"http://localhost:5000/api/health")
runner.assert_status(response, 200, "Health endpoint")

# Test 2: Signup with validation errors
runner.print_test("Signup Validation - Missing Fields")
response = requests.post(f"{BASE_URL}/auth/signup", json={})
runner.assert_status(response, 400, "Should reject empty signup")

# Test 3: Signup with invalid email
runner.print_test("Signup Validation - Invalid Email")
response = requests.post(f"{BASE_URL}/auth/signup", json={
    "email": "invalid-email",
    "password": "Test123!",
    "name": "Test",
    "role": "attendee"
})
runner.assert_status(response, 400, "Should reject invalid email")

# Test 4: Signup with weak password
runner.print_test("Signup Validation - Weak Password")
response = requests.post(f"{BASE_URL}/auth/signup", json={
    "email": f"test{int(time.time())}@gmail.com",
    "password": "weak",
    "name": "Test",
    "role": "attendee"
})
runner.assert_status(response, 400, "Should reject weak password")

# Test 5: Valid Signup (Attendee) - Use gmail.com instead of example.com
runner.print_test("Valid Signup - Attendee")
timestamp = int(time.time())
attendee_email = f"attendee{timestamp}@gmail.com"
signup_data = {
    "email": attendee_email,
    "password": "Attendee123!",
    "name": "Test Attendee",
    "role": "attendee"
}
response = requests.post(f"{BASE_URL}/auth/signup", json=signup_data)
if runner.assert_status(response, 201, "Attendee signup"):
    runner.token = response.json()['data']['session']['access_token']
    runner.user_id = response.json()['data']['user']['id']
    print(f"Token: {runner.token[:30]}...")
    print(f"User ID: {runner.user_id}")

# Test 6: Duplicate Email
runner.print_test("Signup with Duplicate Email")
response = requests.post(f"{BASE_URL}/auth/signup", json=signup_data)
runner.assert_status(response, 400, "Should reject duplicate email")

# Test 7: Login with wrong password
runner.print_test("Login - Wrong Password")
response = requests.post(f"{BASE_URL}/auth/login", json={
    "email": attendee_email,
    "password": "WrongPassword123!"
})
runner.assert_status(response, 401, "Should reject wrong password")

# Test 8: Valid Login
runner.print_test("Valid Login")
response = requests.post(f"{BASE_URL}/auth/login", json={
    "email": attendee_email,
    "password": "Attendee123!"
})
if runner.assert_status(response, 200, "Login successful"):
    runner.token = response.json()['data']['session']['access_token']
    print(f"New token: {runner.token[:30]}...")

# Test 9: Get Current User (Protected Route)
runner.print_test("Get Current User - Protected Route")
headers = {"Authorization": f"Bearer {runner.token}"}
response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
runner.assert_status(response, 200, "Should return user data")

# Test 10: Protected Route without Token
runner.print_test("Protected Route - No Token")
response = requests.get(f"{BASE_URL}/auth/me")
runner.assert_status(response, 401, "Should reject without token")

# Test 11: Protected Route with Invalid Token
runner.print_test("Protected Route - Invalid Token")
bad_headers = {"Authorization": "Bearer invalid-token-xyz"}
response = requests.get(f"{BASE_URL}/auth/me", headers=bad_headers)
runner.assert_status(response, 401, "Should reject invalid token")

# Test 12: Update Profile
runner.print_test("Update Profile")
update_data = {
    "name": "Updated Attendee Name",
    "bio": "I love events!",
    "location": "Karachi, Pakistan"
}
response = requests.put(f"{BASE_URL}/profile", json=update_data, headers=headers)
runner.assert_status(response, 200, "Profile update")

# Test 13: Update Profile without Token
runner.print_test("Update Profile - No Auth")
response = requests.put(f"{BASE_URL}/profile", json=update_data)
runner.assert_status(response, 401, "Should reject without auth")

# Test 14: Get Public Profile
runner.print_test("Get Public Profile")
response = requests.get(f"{BASE_URL}/profile/{runner.user_id}")
runner.assert_status(response, 200, "Get public profile")

# Test 15: Get Non-existent Profile
runner.print_test("Get Non-existent Profile")
fake_uuid = "00000000-0000-0000-0000-000000000000"
response = requests.get(f"{BASE_URL}/profile/{fake_uuid}")
runner.assert_status(response, 404, "Should return 404")

# Test 16: Invalid UUID Format
runner.print_test("Get Profile with Invalid UUID")
response = requests.get(f"{BASE_URL}/profile/not-a-uuid")
runner.assert_status(response, 400, "Should reject invalid UUID")

# Test 17: Switch Role to Organizer
runner.print_test("Switch Role to Organizer")
response = requests.patch(f"{BASE_URL}/profile/role", 
                         json={"role": "organizer"}, 
                         headers=headers)
runner.assert_status(response, 200, "Role update")

# Test 18: Verify Role Change
runner.print_test("Verify Role Change")
response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
if runner.assert_status(response, 200, "Get user after role change"):
    role = response.json()['data']['role']
    if role == "organizer":
        print(f"✅ Role correctly updated to: {role}")
        runner.passed += 1
    else:
        print(f"❌ Role should be 'organizer', got: {role}")
        runner.failed += 1

# Test 19: Invalid Role
runner.print_test("Update with Invalid Role")
response = requests.patch(f"{BASE_URL}/profile/role", 
                         json={"role": "admin"}, 
                         headers=headers)
runner.assert_status(response, 400, "Should reject invalid role")

# Test 20: Create Organizer Account
runner.print_test("Create Organizer Account")
organizer_email = f"organizer{int(time.time())}@gmail.com"
response = requests.post(f"{BASE_URL}/auth/signup", json={
    "email": organizer_email,
    "password": "Organizer123!",
    "name": "Test Organizer",
    "role": "organizer"
})
if runner.assert_status(response, 201, "Organizer signup"):
    org_token = response.json()['data']['session']['access_token']
    org_headers = {"Authorization": f"Bearer {org_token}"}
    
    # Verify organizer role
    response = requests.get(f"{BASE_URL}/auth/me", headers=org_headers)
    if response.status_code == 200:
        role = response.json()['data']['role']
        if role == "organizer":
            print(f"✅ Organizer role correctly set")
            runner.passed += 1
        else:
            print(f"❌ Expected organizer role, got: {role}")
            runner.failed += 1

# Test 21: Logout
runner.print_test("Logout")
response = requests.post(f"{BASE_URL}/auth/logout", headers=headers)
runner.assert_status(response, 200, "Logout")

# Print summary
runner.print_summary()

if runner.failed == 0:
    print("\n🎉 ALL TESTS PASSED! 🎉")
    print("Your EventSaga backend is working perfectly!")
else:
    print(f"\n⚠️  {runner.failed} test(s) failed. Check the output above.")