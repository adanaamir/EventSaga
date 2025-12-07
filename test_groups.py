import requests
import json
import time

BASE_URL = "http://localhost:5000/api"

class TestRunner:
    def __init__(self):
        self.user1_token = None
        self.user2_token = None
        self.group_id = None
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
            try:
                print(json.dumps(response.json(), indent=2))
            except:
                print(response.text)
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

# Setup: Create test users
runner.print_test("Setup: Create User 1")
timestamp = int(time.time())
user1_email = f"groupuser1_{timestamp}@gmail.com"
response = requests.post(f"{BASE_URL}/auth/signup", json={
    "email": user1_email,
    "password": "User123!",
    "name": "Group User 1",
    "role": "attendee"
})
if runner.assert_status(response, 201, "User 1 signup"):
    runner.user1_token = response.json()['data']['session']['access_token']
    print(f"User 1 token: {runner.user1_token[:30]}...")

runner.print_test("Setup: Create User 2")
user2_email = f"groupuser2_{timestamp}@gmail.com"
response = requests.post(f"{BASE_URL}/auth/signup", json={
    "email": user2_email,
    "password": "User123!",
    "name": "Group User 2",
    "role": "attendee"
})
if runner.assert_status(response, 201, "User 2 signup"):
    runner.user2_token = response.json()['data']['session']['access_token']
    print(f"User 2 token: {runner.user2_token[:30]}...")

user1_headers = {"Authorization": f"Bearer {runner.user1_token}"}
user2_headers = {"Authorization": f"Bearer {runner.user2_token}"}

# Test 1: Create group with validation errors
runner.print_test("Create Group - Validation Errors")
bad_group = {
    "name": "AB",  # Too short
    "description": "Short"  # Too short
}
response = requests.post(f"{BASE_URL}/groups", json=bad_group, headers=user1_headers)
runner.assert_status(response, 400, "Should reject invalid data")

# Test 2: Create group successfully
runner.print_test("Create Group - Success")
group_data = {
    "name": "Tech Enthusiasts Karachi",
    "description": "A community for tech lovers in Karachi to share knowledge and network",
    "category": "tech",
    "is_public": True
}
response = requests.post(f"{BASE_URL}/groups", json=group_data, headers=user1_headers)
if runner.assert_status(response, 201, "Group creation"):
    runner.group_id = response.json()['data']['id']
    print(f"Created group ID: {runner.group_id}")
    group = response.json()['data']
    if group['member_count'] == 1 and group['user_is_member'] and group['user_role'] == 'admin':
        print("✅ Creator automatically added as admin")
        runner.passed += 1
    else:
        print("❌ Creator membership not correct")
        runner.failed += 1

# Test 3: List all groups (public)
runner.print_test("List All Groups - Public")
response = requests.get(f"{BASE_URL}/groups")
if runner.assert_status(response, 200, "List groups"):
    groups = response.json()['data']['groups']
    if len(groups) > 0:
        print(f"✅ Found {len(groups)} group(s)")
        runner.passed += 1

# Test 4: Filter groups by category
runner.print_test("Filter Groups by Category")
response = requests.get(f"{BASE_URL}/groups?category=tech")
runner.assert_status(response, 200, "Filter by category")

# Test 5: Search groups
runner.print_test("Search Groups")
response = requests.get(f"{BASE_URL}/groups?search=tech")
runner.assert_status(response, 200, "Search groups")

# Test 6: Get single group details
runner.print_test("Get Group Details")
response = requests.get(f"{BASE_URL}/groups/{runner.group_id}")
if runner.assert_status(response, 200, "Get group details"):
    group = response.json()['data']
    print(f"Group name: {group['name']}")
    print(f"Member count: {group['member_count']}")
    print(f"Category: {group['category']}")

# Test 7: Get non-existent group
runner.print_test("Get Non-existent Group")
fake_id = "00000000-0000-0000-0000-000000000000"
response = requests.get(f"{BASE_URL}/groups/{fake_id}")
runner.assert_status(response, 404, "Should return 404")

# Test 8: User 2 joins group
runner.print_test("Join Group - User 2")
response = requests.post(f"{BASE_URL}/groups/{runner.group_id}/join", headers=user2_headers)
runner.assert_status(response, 201, "Join group")

# Test 9: Duplicate join (should fail)
runner.print_test("Duplicate Join (Should Fail)")
response = requests.post(f"{BASE_URL}/groups/{runner.group_id}/join", headers=user2_headers)
runner.assert_status(response, 400, "Should reject duplicate join")

# Test 10: Verify member count increased
runner.print_test("Verify Member Count After Join")
response = requests.get(f"{BASE_URL}/groups/{runner.group_id}")
if runner.assert_status(response, 200, "Get group"):
    group = response.json()['data']
    if group['member_count'] == 2:
        print("✅ Member count correctly updated to 2")
        runner.passed += 1
    else:
        print(f"❌ Member count is {group['member_count']}, expected 2")
        runner.failed += 1

# Test 11: Get group members
runner.print_test("Get Group Members")
response = requests.get(f"{BASE_URL}/groups/{runner.group_id}/members", headers=user1_headers)
if runner.assert_status(response, 200, "Get members"):
    members = response.json()['data']['members']
    if len(members) == 2:
        print(f"✅ Found {len(members)} members")
        runner.passed += 1
        # Check roles
        admin_count = sum(1 for m in members if m['role'] == 'admin')
        member_count = sum(1 for m in members if m['role'] == 'member')
        print(f"   Admins: {admin_count}, Members: {member_count}")
        if admin_count == 1 and member_count == 1:
            print("✅ Roles correctly assigned")
            runner.passed += 1

# Test 12: Get user's groups
runner.print_test("Get User's Groups - User 1")
response = requests.get(f"{BASE_URL}/groups/my-groups", headers=user1_headers)
if runner.assert_status(response, 200, "Get my groups"):
    groups = response.json()['data']['groups']
    if len(groups) > 0:
        print(f"✅ User 1 is in {len(groups)} group(s)")
        runner.passed += 1

runner.print_test("Get User's Groups - User 2")
response = requests.get(f"{BASE_URL}/groups/my-groups", headers=user2_headers)
if runner.assert_status(response, 200, "Get my groups"):
    groups = response.json()['data']['groups']
    if len(groups) > 0:
        print(f"✅ User 2 is in {len(groups)} group(s)")
        runner.passed += 1

# Test 13: Non-member tries to view members of public group (should succeed)
runner.print_test("Non-member Views Public Group Members")
user3_email = f"groupuser3_{timestamp}@gmail.com"
response = requests.post(f"{BASE_URL}/auth/signup", json={
    "email": user3_email,
    "password": "User123!",
    "name": "Group User 3",
    "role": "attendee"
})
if response.status_code == 201:
    user3_token = response.json()['data']['session']['access_token']
    user3_headers = {"Authorization": f"Bearer {user3_token}"}
    
    response = requests.get(f"{BASE_URL}/groups/{runner.group_id}/members", headers=user3_headers)
    runner.assert_status(response, 200, "Public group members viewable by non-members")

# Test 14: User 2 leaves group
runner.print_test("Leave Group - User 2")
response = requests.delete(f"{BASE_URL}/groups/{runner.group_id}/leave", headers=user2_headers)
runner.assert_status(response, 200, "Leave group")

# Test 15: Verify member count decreased
runner.print_test("Verify Member Count After Leave")
response = requests.get(f"{BASE_URL}/groups/{runner.group_id}")
if runner.assert_status(response, 200, "Get group"):
    group = response.json()['data']
    if group['member_count'] == 1:
        print("✅ Member count correctly updated to 1")
        runner.passed += 1
    else:
        print(f"❌ Member count is {group['member_count']}, expected 1")
        runner.failed += 1

# Test 16: Non-member tries to leave (should fail)
runner.print_test("Non-member Leaves Group (Should Fail)")
response = requests.delete(f"{BASE_URL}/groups/{runner.group_id}/leave", headers=user2_headers)
runner.assert_status(response, 404, "Should return 404")

# Test 17: Only admin tries to leave (should fail)
runner.print_test("Only Admin Leaves Group (Should Fail)")
response = requests.delete(f"{BASE_URL}/groups/{runner.group_id}/leave", headers=user1_headers)
runner.assert_status(response, 400, "Should prevent only admin from leaving")

# Test 18: Create private group
runner.print_test("Create Private Group")
private_group_data = {
    "name": "VIP Tech Club",
    "description": "Exclusive tech community for selected members",
    "category": "tech",
    "is_public": False
}
response = requests.post(f"{BASE_URL}/groups", json=private_group_data, headers=user1_headers)
if runner.assert_status(response, 201, "Private group creation"):
    private_group_id = response.json()['data']['id']
    
    # Test 19: Non-member tries to join private group (should fail)
    runner.print_test("Join Private Group (Should Fail)")
    response = requests.post(f"{BASE_URL}/groups/{private_group_id}/join", headers=user2_headers)
    runner.assert_status(response, 400, "Should reject joining private group")
    
    # Test 20: Non-member tries to view private group (should fail)
    runner.print_test("View Private Group - Non-member (Should Fail)")
    response = requests.get(f"{BASE_URL}/groups/{private_group_id}", headers=user2_headers)
    runner.assert_status(response, 404, "Should not show private group to non-members")

# Print summary
runner.print_summary()

if runner.failed == 0:
    print("\n🎉 ALL PHASE 3 TESTS PASSED! 🎉")
    print("Community groups system working perfectly!")
else:
    print(f"\n⚠️  {runner.failed} test(s) failed. Check the output above.")