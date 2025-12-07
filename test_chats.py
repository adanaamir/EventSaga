"""
Test Suite for Real-Time Messaging (Phase 4)
Tests all messaging functionality within groups
"""
import requests
import json
import time

BASE_URL = "http://localhost:5000/api"

class TestRunner:
    def __init__(self):
        self.user1_token = None
        self.user2_token = None
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

# Setup: Create test users
runner.print_test("Setup: Create User 1")
timestamp = int(time.time())
user1_email = f"chatuser1_{timestamp}@gmail.com"
response = requests.post(f"{BASE_URL}/auth/signup", json={
    "email": user1_email,
    "password": "User123!",
    "name": "Chat User 1",
    "role": "attendee"
})
if runner.assert_status(response, 201, "User 1 signup"):
    runner.user1_token = response.json()['data']['session']['access_token']
    print(f"User 1 token: {runner.user1_token[:30]}...")

runner.print_test("Setup: Create User 2")
user2_email = f"chatuser2_{timestamp}@gmail.com"
response = requests.post(f"{BASE_URL}/auth/signup", json={
    "email": user2_email,
    "password": "User123!",
    "name": "Chat User 2",
    "role": "attendee"
})
if runner.assert_status(response, 201, "User 2 signup"):
    runner.user2_token = response.json()['data']['session']['access_token']
    print(f"User 2 token: {runner.user2_token[:30]}...")

user1_headers = {"Authorization": f"Bearer {runner.user1_token}"}
user2_headers = {"Authorization": f"Bearer {runner.user2_token}"}

# Setup: Create a group
runner.print_test("Setup: Create Group")
group_data = {
    "name": "Chat Test Group",
    "description": "A group for testing chat functionality",
    "category": "tech",
    "is_public": True
}
response = requests.post(f"{BASE_URL}/groups", json=group_data, headers=user1_headers)
if runner.assert_status(response, 201, "Group creation"):
    runner.group_id = response.json()['data']['id']
    print(f"Created group ID: {runner.group_id}")

# Setup: User 2 joins group
runner.print_test("Setup: User 2 Joins Group")
response = requests.post(f"{BASE_URL}/groups/{runner.group_id}/join", headers=user2_headers)
runner.assert_status(response, 201, "User 2 joins group")

# Test 1: Non-member tries to view messages (should fail)
runner.print_test("View Messages - Non-member (Should Fail)")
user3_email = f"chatuser3_{timestamp}@gmail.com"
response = requests.post(f"{BASE_URL}/auth/signup", json={
    "email": user3_email,
    "password": "User123!",
    "name": "Chat User 3",
    "role": "attendee"
})
if response.status_code == 201:
    user3_token = response.json()['data']['session']['access_token']
    user3_headers = {"Authorization": f"Bearer {user3_token}"}
    
    response = requests.get(f"{BASE_URL}/groups/{runner.group_id}/messages", headers=user3_headers)
    runner.assert_status(response, 403, "Should reject non-member")

# Test 2: Get messages (empty at first)
runner.print_test("Get Messages - Empty Group")
response = requests.get(f"{BASE_URL}/groups/{runner.group_id}/messages", headers=user1_headers)
if runner.assert_status(response, 200, "Get messages"):
    messages = response.json()['data']['messages']
    if len(messages) == 0:
        print("✅ No messages in new group")
        runner.passed += 1

# Test 3: Send message with validation errors
runner.print_test("Send Message - Empty Content (Should Fail)")
response = requests.post(f"{BASE_URL}/groups/{runner.group_id}/messages", 
                        json={"content": ""}, 
                        headers=user1_headers)
runner.assert_status(response, 400, "Should reject empty message")

runner.print_test("Send Message - Too Long (Should Fail)")
long_message = "x" * 2001
response = requests.post(f"{BASE_URL}/groups/{runner.group_id}/messages", 
                        json={"content": long_message}, 
                        headers=user1_headers)
runner.assert_status(response, 400, "Should reject too long message")

# Test 4: User 1 sends first message
runner.print_test("Send Message - User 1")
message_data = {"content": "Hello everyone! Welcome to the group."}
response = requests.post(f"{BASE_URL}/groups/{runner.group_id}/messages", 
                        json=message_data, 
                        headers=user1_headers)
if runner.assert_status(response, 201, "Message sent"):
    runner.message_id = response.json()['data']['id']
    print(f"Message ID: {runner.message_id}")

# Test 5: User 2 sends message
runner.print_test("Send Message - User 2")
message_data = {"content": "Thanks for creating this group!"}
response = requests.post(f"{BASE_URL}/groups/{runner.group_id}/messages", 
                        json=message_data, 
                        headers=user2_headers)
runner.assert_status(response, 201, "Message sent")

# Test 6: User 1 sends another message
runner.print_test("Send Message - User 1 Again")
message_data = {"content": "Let's discuss some interesting tech topics!"}
response = requests.post(f"{BASE_URL}/groups/{runner.group_id}/messages", 
                        json=message_data, 
                        headers=user1_headers)
runner.assert_status(response, 201, "Message sent")

# Test 7: Get all messages
runner.print_test("Get All Messages")
response = requests.get(f"{BASE_URL}/groups/{runner.group_id}/messages", headers=user1_headers)
if runner.assert_status(response, 200, "Get messages"):
    data = response.json()['data']
    messages = data['messages']
    if len(messages) == 3:
        print(f"✅ Found {len(messages)} messages")
        runner.passed += 1
        print(f"\nMessages in chronological order:")
        for i, msg in enumerate(messages, 1):
            print(f"{i}. [{msg['sender']['name']}]: {msg['content']}")
    else:
        print(f"❌ Expected 3 messages, got {len(messages)}")
        runner.failed += 1

# Test 8: Send more messages for pagination testing
runner.print_test("Send Multiple Messages for Pagination")
for i in range(5):
    message_data = {"content": f"Test message {i+1} for pagination"}
    response = requests.post(f"{BASE_URL}/groups/{runner.group_id}/messages", 
                            json=message_data, 
                            headers=user1_headers)
    if response.status_code != 201:
        print(f"❌ Failed to send message {i+1}")
        runner.failed += 1
        break
else:
    print("✅ Sent 5 additional messages")
    runner.passed += 1

# Test 9: Get messages with limit
runner.print_test("Get Messages with Limit")
response = requests.get(f"{BASE_URL}/groups/{runner.group_id}/messages?limit=5", 
                       headers=user1_headers)
if runner.assert_status(response, 200, "Get limited messages"):
    data = response.json()['data']
    messages = data['messages']
    if len(messages) == 5:
        print(f"✅ Correctly limited to 5 messages")
        runner.passed += 1
    else:
        print(f"❌ Expected 5 messages, got {len(messages)}")
        runner.failed += 1

# Test 10: Non-member tries to send message (should fail)
runner.print_test("Send Message - Non-member (Should Fail)")
message_data = {"content": "I'm not a member!"}
response = requests.post(f"{BASE_URL}/groups/{runner.group_id}/messages", 
                        json=message_data, 
                        headers=user3_headers)
runner.assert_status(response, 403, "Should reject non-member")

# Test 11: User 1 deletes their own message
runner.print_test("Delete Message - Owner")
response = requests.delete(f"{BASE_URL}/groups/{runner.group_id}/messages/{runner.message_id}", 
                          headers=user1_headers)
runner.assert_status(response, 200, "Delete own message")

# Test 12: Verify deleted message not in list
runner.print_test("Verify Deleted Message Not in List")
response = requests.get(f"{BASE_URL}/groups/{runner.group_id}/messages", headers=user1_headers)
if runner.assert_status(response, 200, "Get messages"):
    messages = response.json()['data']['messages']
    deleted_msg = next((m for m in messages if m['id'] == runner.message_id), None)
    if deleted_msg is None:
        print("✅ Deleted message not in list")
        runner.passed += 1
    else:
        print("❌ Deleted message still appears in list")
        runner.failed += 1

# Test 13: User 2 tries to delete User 1's message (should fail)
runner.print_test("Delete Message - Non-owner (Should Fail)")
# Get a message from User 1 (not the deleted one)
response = requests.get(f"{BASE_URL}/groups/{runner.group_id}/messages", headers=user1_headers)
if response.status_code == 200:
    messages = response.json()['data']['messages']
    user1_messages = [m for m in messages if m['sender']['name'] == 'Chat User 1']
    if user1_messages:
        msg_to_delete = user1_messages[0]['id']
        response = requests.delete(f"{BASE_URL}/groups/{runner.group_id}/messages/{msg_to_delete}", 
                                  headers=user2_headers)
        runner.assert_status(response, 403, "Should reject non-owner deletion")

# Test 14: Get message count
runner.print_test("Verify Total Message Count")
response = requests.get(f"{BASE_URL}/groups/{runner.group_id}/messages", headers=user1_headers)
if runner.assert_status(response, 200, "Get all messages"):
    count = response.json()['data']['count']
    print(f"Total messages in group: {count}")
    if count >= 5:  # At least 5 messages should remain (after deletion)
        print(f"✅ Message count is correct")
        runner.passed += 1

# Test 15: Invalid group ID
runner.print_test("Get Messages - Invalid Group ID")
fake_id = "00000000-0000-0000-0000-000000000000"
response = requests.get(f"{BASE_URL}/groups/{fake_id}/messages", headers=user1_headers)
runner.assert_status(response, 403, "Should reject invalid group or non-membership")

# Test 16: Send message with special characters
runner.print_test("Send Message with Special Characters")
message_data = {"content": "Testing emojis 🎉🚀 and symbols @#$%^&*()"}
response = requests.post(f"{BASE_URL}/groups/{runner.group_id}/messages", 
                        json=message_data, 
                        headers=user1_headers)
runner.assert_status(response, 201, "Message with special chars")

# Test 17: Verify chronological order
runner.print_test("Verify Messages in Chronological Order")
response = requests.get(f"{BASE_URL}/groups/{runner.group_id}/messages", headers=user1_headers)
if runner.assert_status(response, 200, "Get messages"):
    messages = response.json()['data']['messages']
    if len(messages) > 1:
        # Check if messages are in chronological order (oldest first)
        is_sorted = all(messages[i]['created_at'] <= messages[i+1]['created_at'] 
                       for i in range(len(messages)-1))
        if is_sorted:
            print("✅ Messages correctly sorted in chronological order (oldest first)")
            runner.passed += 1
        else:
            print("❌ Messages not in correct chronological order")
            runner.failed += 1

# Print summary
runner.print_summary()

if runner.failed == 0:
    print("\n🎉 ALL PHASE 4 TESTS PASSED! 🎉")
    print("Real-time chat system working perfectly!")
else:
    print(f"\n⚠️  {runner.failed} test(s) failed. Check the output above.")