"""
EventSaga Backend - Complete Test Suite
Tests all phases: Auth, Profile, Events, RSVPs, Groups, and Messaging
"""
import requests
import json
import time
from datetime import datetime, timedelta

BASE_URL = "http://localhost:5000/api"

class TestRunner:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.organizer_token = None
        self.user2_token = None
        self.event_id = None
        self.group_id = None
        self.message_id = None
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

print("=" * 60)
print("EVENTSAGA BACKEND - COMPLETE TEST SUITE")
print("Testing Phases 1-4: Auth, Profile, Events, RSVPs, Groups, Messaging")
print("=" * 60)

# ============================================================================
# PHASE 1: AUTHENTICATION & PROFILE TESTS
# ============================================================================

print("\n" + "🔐 PHASE 1: AUTHENTICATION & PROFILE TESTS" + "\n")

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

# Test 4: Valid Signup (Attendee)
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

# Test 5: Valid Login
runner.print_test("Valid Login")
response = requests.post(f"{BASE_URL}/auth/login", json={
    "email": attendee_email,
    "password": "Attendee123!"
})
if runner.assert_status(response, 200, "Login successful"):
    runner.token = response.json()['data']['session']['access_token']

headers = {"Authorization": f"Bearer {runner.token}"}

# Test 6: Get Current User
runner.print_test("Get Current User - Protected Route")
response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
runner.assert_status(response, 200, "Should return user data")

# Test 7: Update Profile
runner.print_test("Update Profile")
update_data = {
    "name": "Updated Attendee Name",
    "bio": "I love events!",
    "location": "Karachi, Pakistan"
}
response = requests.put(f"{BASE_URL}/profile", json=update_data, headers=headers)
runner.assert_status(response, 200, "Profile update")

# Test 8: Switch Role to Organizer
runner.print_test("Switch Role to Organizer")
response = requests.patch(f"{BASE_URL}/profile/role", 
                         json={"role": "organizer"}, 
                         headers=headers)
runner.assert_status(response, 200, "Role update")

# ============================================================================
# PHASE 2: EVENT & RSVP TESTS
# ============================================================================

print("\n" + "PHASE 2: EVENT & RSVP TESTS" + "\n")

# Test 9: Create Event (now user is organizer)
runner.print_test("Create Event - Organizer")
future_date = (datetime.now() + timedelta(days=30)).isoformat() + 'Z'
event_data = {
    "title": "Tech Conference 2025",
    "description": "Annual technology conference featuring latest innovations",
    "datetime": future_date,
    "location": "Convention Center",
    "city": "Karachi",
    "category": "tech",
    "capacity": 100
}
response = requests.post(f"{BASE_URL}/events", json=event_data, headers=headers)
if runner.assert_status(response, 201, "Event creation"):
    runner.event_id = response.json()['data']['id']
    print(f"Created event ID: {runner.event_id}")

# Test 10: List All Events
runner.print_test("List All Events")
response = requests.get(f"{BASE_URL}/events")
runner.assert_status(response, 200, "List events")

# Test 11: Get Event Details
runner.print_test("Get Event Details")
response = requests.get(f"{BASE_URL}/events/{runner.event_id}")
runner.assert_status(response, 200, "Get event details")

# Test 12: Create Second User for RSVP Tests
runner.print_test("Create Second User")
user2_email = f"user2_{timestamp}@gmail.com"
response = requests.post(f"{BASE_URL}/auth/signup", json={
    "email": user2_email,
    "password": "User123!",
    "name": "Test User 2",
    "role": "attendee"
})
if runner.assert_status(response, 201, "User 2 signup"):
    runner.user2_token = response.json()['data']['session']['access_token']

user2_headers = {"Authorization": f"Bearer {runner.user2_token}"}

# Test 13: RSVP to Event
runner.print_test("RSVP to Event")
response = requests.post(f"{BASE_URL}/rsvps/{runner.event_id}", headers=user2_headers)
runner.assert_status(response, 201, "RSVP creation")

# Test 14: Get User's RSVPs
runner.print_test("Get User's RSVPs")
response = requests.get(f"{BASE_URL}/rsvps/my-rsvps", headers=user2_headers)
runner.assert_status(response, 200, "Get my RSVPs")

# Test 15: Cancel RSVP
runner.print_test("Cancel RSVP")
response = requests.delete(f"{BASE_URL}/rsvps/{runner.event_id}", headers=user2_headers)
runner.assert_status(response, 200, "Cancel RSVP")

# ============================================================================
# PHASE 3: COMMUNITY GROUPS TESTS
# ============================================================================

print("\n" + "PHASE 3: COMMUNITY GROUPS TESTS" + "\n")

# Test 16: Create Group
runner.print_test("Create Group")
group_data = {
    "name": "Tech Enthusiasts Karachi",
    "description": "A community for tech lovers in Karachi to share knowledge and network",
    "category": "tech",
    "is_public": True
}
response = requests.post(f"{BASE_URL}/groups", json=group_data, headers=headers)
if runner.assert_status(response, 201, "Group creation"):
    runner.group_id = response.json()['data']['id']
    print(f"Created group ID: {runner.group_id}")
    group = response.json()['data']
    if group['member_count'] == 1 and group['user_is_member'] and group['user_role'] == 'admin':
        print("✅ Creator automatically added as admin")
        runner.passed += 1

# Test 17: List All Groups
runner.print_test("List All Groups")
response = requests.get(f"{BASE_URL}/groups")
runner.assert_status(response, 200, "List groups")

# Test 18: Get Group Details
runner.print_test("Get Group Details")
response = requests.get(f"{BASE_URL}/groups/{runner.group_id}")
runner.assert_status(response, 200, "Get group details")

# Test 19: User 2 Joins Group
runner.print_test("Join Group - User 2")
response = requests.post(f"{BASE_URL}/groups/{runner.group_id}/join", headers=user2_headers)
runner.assert_status(response, 201, "Join group")

# Test 20: Get Group Members
runner.print_test("Get Group Members")
response = requests.get(f"{BASE_URL}/groups/{runner.group_id}/members", headers=headers)
if runner.assert_status(response, 200, "Get members"):
    members = response.json()['data']['members']
    if len(members) == 2:
        print(f"✅ Found {len(members)} members")
        runner.passed += 1

# Test 21: Get User's Groups
runner.print_test("Get User's Groups")
response = requests.get(f"{BASE_URL}/groups/my-groups", headers=headers)
if runner.assert_status(response, 200, "Get my groups"):
    groups = response.json()['data']['groups']
    if len(groups) > 0:
        print(f"✅ User is in {len(groups)} group(s)")
        runner.passed += 1

# ============================================================================
# PHASE 4: REAL-TIME MESSAGING TESTS
# ============================================================================

print("\n" + "PHASE 4: REAL-TIME MESSAGING TESTS" + "\n")

# Test 22: Get Messages (Empty at First)
runner.print_test("Get Messages - Empty Group")
response = requests.get(f"{BASE_URL}/groups/{runner.group_id}/messages", headers=headers)
if runner.assert_status(response, 200, "Get messages"):
    messages = response.json()['data']['messages']
    if len(messages) == 0:
        print("✅ No messages in new group")
        runner.passed += 1

# Test 23: Send Message - User 1
runner.print_test("Send Message - User 1")
message_data = {"content": "Hello everyone! Welcome to the group."}
response = requests.post(f"{BASE_URL}/groups/{runner.group_id}/messages", 
                        json=message_data, 
                        headers=headers)
if runner.assert_status(response, 201, "Message sent"):
    runner.message_id = response.json()['data']['id']
    print(f"Message ID: {runner.message_id}")

# Test 24: Send Message - User 2
runner.print_test("Send Message - User 2")
message_data = {"content": "Thanks for creating this group!"}
response = requests.post(f"{BASE_URL}/groups/{runner.group_id}/messages", 
                        json=message_data, 
                        headers=user2_headers)
runner.assert_status(response, 201, "Message sent")

# Test 25: Send Another Message - User 1
runner.print_test("Send Message - User 1 Again")
message_data = {"content": "Let's discuss some interesting tech topics!"}
response = requests.post(f"{BASE_URL}/groups/{runner.group_id}/messages", 
                        json=message_data, 
                        headers=headers)
runner.assert_status(response, 201, "Message sent")

# Test 26: Get All Messages
runner.print_test("Get All Messages")
response = requests.get(f"{BASE_URL}/groups/{runner.group_id}/messages", headers=headers)
if runner.assert_status(response, 200, "Get messages"):
    data = response.json()['data']
    messages = data['messages']
    if len(messages) == 3:
        print(f"✅ Found {len(messages)} messages")
        runner.passed += 1
        print(f"\nMessages in chronological order:")
        for i, msg in enumerate(messages, 1):
            print(f"{i}. [{msg['sender']['name']}]: {msg['content'][:50]}...")

# Test 28: Delete Own Message
runner.print_test("Delete Message - Owner")
response = requests.delete(f"{BASE_URL}/groups/{runner.group_id}/messages/{runner.message_id}", 
                          headers=headers)
runner.assert_status(response, 200, "Delete own message")

# Test 30: Send Message with Special Characters
runner.print_test("Send Message with Special Characters")
message_data = {"content": "Testing emojis 🎉🚀 and symbols @#$%^&*()"}
response = requests.post(f"{BASE_URL}/groups/{runner.group_id}/messages", 
                        json=message_data, 
                        headers=headers)
runner.assert_status(response, 201, "Message with special chars")

# ============================================================================
# CLEANUP & FINAL TESTS
# ============================================================================

print("\n" + "🧹 CLEANUP & FINAL TESTS" + "\n")

# Test 31: User 2 Leaves Group
runner.print_test("Leave Group - User 2")
response = requests.delete(f"{BASE_URL}/groups/{runner.group_id}/leave", headers=user2_headers)
runner.assert_status(response, 200, "Leave group")

# Test 32: Update Event
runner.print_test("Update Event")
update_data = {"title": "Updated Tech Conference 2025", "capacity": 150}
response = requests.put(f"{BASE_URL}/events/{runner.event_id}", json=update_data, headers=headers)
runner.assert_status(response, 200, "Event update")

# Test 33: Get Organizer's Events
runner.print_test("Get Organizer's Events")
response = requests.get(f"{BASE_URL}/events/organizer/my-events", headers=headers)
runner.assert_status(response, 200, "Get my events")

# Test 34: Logout
runner.print_test("Logout")
response = requests.post(f"{BASE_URL}/auth/logout", headers=headers)
runner.assert_status(response, 200, "Logout")

# ============================================================================
# FINAL SUMMARY
# ============================================================================

runner.print_summary()

if runner.failed == 0:
    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED! 🎉")
    print("=" * 60)
    print("✅ Phase 1: Authentication & Profile - WORKING")
    print("✅ Phase 2: Events & RSVPs - WORKING")
    print("✅ Phase 3: Community Groups - WORKING")
    print("✅ Phase 4: Real-Time Messaging - WORKING")
    print("=" * 60)
    print("Your EventSaga backend is fully functional!")
    print("=" * 60)
else:
    print("\n" + "=" * 60)
    print(f"⚠️  {runner.failed} test(s) failed")
    print("=" * 60)
    print("Check the output above for details.")
    print("=" * 60)