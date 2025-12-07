import requests
import json
import time
from datetime import datetime, timedelta

BASE_URL = "http://localhost:5000/api"

class TestRunner:
    def __init__(self):
        self.organizer_token = None
        self.attendee_token = None
        self.event_id = None
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
runner.print_test("Setup: Create Organizer Account")
timestamp = int(time.time())
organizer_email = f"organizer{timestamp}@gmail.com"
response = requests.post(f"{BASE_URL}/auth/signup", json={
    "email": organizer_email,
    "password": "Organizer123!",
    "name": "Test Organizer",
    "role": "organizer"
})
if runner.assert_status(response, 201, "Organizer signup"):
    runner.organizer_token = response.json()['data']['session']['access_token']
    print(f"Organizer token: {runner.organizer_token[:30]}...")

runner.print_test("Setup: Create Attendee Account")
attendee_email = f"attendee{timestamp}@gmail.com"
response = requests.post(f"{BASE_URL}/auth/signup", json={
    "email": attendee_email,
    "password": "Attendee123!",
    "name": "Test Attendee",
    "role": "attendee"
})
if runner.assert_status(response, 201, "Attendee signup"):
    runner.attendee_token = response.json()['data']['session']['access_token']
    print(f"Attendee token: {runner.attendee_token[:30]}...")

# Test 1: Attendee tries to create event (should fail)
runner.print_test("Create Event - Attendee (Should Fail)")
org_headers = {"Authorization": f"Bearer {runner.organizer_token}"}
att_headers = {"Authorization": f"Bearer {runner.attendee_token}"}

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

response = requests.post(f"{BASE_URL}/events", json=event_data, headers=att_headers)
runner.assert_status(response, 403, "Should reject non-organizer")

# Test 2: Organizer creates event successfully
runner.print_test("Create Event - Organizer")
response = requests.post(f"{BASE_URL}/events", json=event_data, headers=org_headers)
if runner.assert_status(response, 201, "Event creation"):
    runner.event_id = response.json()['data']['id']
    print(f"Created event ID: {runner.event_id}")

# Test 3: Create event with validation errors
runner.print_test("Create Event - Validation Errors")
bad_event = {
    "title": "AB",  # Too short
    "description": "Short",  # Too short
    "datetime": future_date,
    "location": "X",  # Too short
    "city": "K",  # Too short
    "category": "invalid"  # Invalid category
}
response = requests.post(f"{BASE_URL}/events", json=bad_event, headers=org_headers)
runner.assert_status(response, 400, "Should reject invalid data")

# Test 4: List all events (public)
runner.print_test("List All Events - Public")
response = requests.get(f"{BASE_URL}/events")
runner.assert_status(response, 200, "List events")

# Test 5: Filter events by city
runner.print_test("Filter Events by City")
response = requests.get(f"{BASE_URL}/events?city=Karachi")
if runner.assert_status(response, 200, "Filter by city"):
    events = response.json()['data']['events']
    if len(events) > 0:
        print(f"✅ Found {len(events)} event(s) in Karachi")
        runner.passed += 1
    else:
        print("❌ No events found")
        runner.failed += 1

# Test 6: Filter events by category
runner.print_test("Filter Events by Category")
response = requests.get(f"{BASE_URL}/events?category=tech")
runner.assert_status(response, 200, "Filter by category")

# Test 7: Search events
runner.print_test("Search Events")
response = requests.get(f"{BASE_URL}/events?search=conference")
runner.assert_status(response, 200, "Search events")

# Test 8: Get single event details
runner.print_test("Get Event Details")
response = requests.get(f"{BASE_URL}/events/{runner.event_id}")
if runner.assert_status(response, 200, "Get event details"):
    event = response.json()['data']
    print(f"Event title: {event['title']}")
    print(f"RSVP count: {event['rsvp_count']}")
    print(f"User has RSVP'd: {event['user_has_rsvped']}")

# Test 9: Get non-existent event
runner.print_test("Get Non-existent Event")
fake_id = "00000000-0000-0000-0000-000000000000"
response = requests.get(f"{BASE_URL}/events/{fake_id}")
runner.assert_status(response, 404, "Should return 404")

# Test 10: Get trending events
runner.print_test("Get Trending Events")
response = requests.get(f"{BASE_URL}/events/trending")
runner.assert_status(response, 200, "Get trending events")

# Test 11: Update event (organizer)
runner.print_test("Update Event - Organizer")
update_data = {
    "title": "Updated Tech Conference 2025",
    "capacity": 150
}
response = requests.put(f"{BASE_URL}/events/{runner.event_id}", json=update_data, headers=org_headers)
runner.assert_status(response, 200, "Event update")

# Test 12: Update event (non-owner, should fail)
runner.print_test("Update Event - Non-owner (Should Fail)")
response = requests.put(f"{BASE_URL}/events/{runner.event_id}", json=update_data, headers=att_headers)
runner.assert_status(response, 403, "Should reject non-owner")

# Test 13: Get organizer's events
runner.print_test("Get Organizer's Events")
response = requests.get(f"{BASE_URL}/events/organizer/my-events", headers=org_headers)
if runner.assert_status(response, 200, "Get my events"):
    events = response.json()['data']['events']
    if len(events) > 0:
        print(f"✅ Organizer has {len(events)} event(s)")
        runner.passed += 1

# Test 14: Attendee RSVPs to event
runner.print_test("RSVP to Event - Attendee")
response = requests.post(f"{BASE_URL}/rsvps/{runner.event_id}", headers=att_headers)
runner.assert_status(response, 201, "RSVP creation")

# Test 15: Duplicate RSVP (should fail)
runner.print_test("Duplicate RSVP (Should Fail)")
response = requests.post(f"{BASE_URL}/rsvps/{runner.event_id}", headers=att_headers)
runner.assert_status(response, 400, "Should reject duplicate RSVP")

# Test 16: Verify RSVP status in event details
runner.print_test("Verify RSVP Status in Event Details")
response = requests.get(f"{BASE_URL}/events/{runner.event_id}", headers=att_headers)
if runner.assert_status(response, 200, "Get event with auth"):
    event = response.json()['data']
    if event['user_has_rsvped']:
        print("✅ User RSVP status correctly reflected in event details")
        runner.passed += 1
    else:
        print("❌ RSVP status not reflected")
        runner.failed += 1

# Test 17: Get user's RSVPs
runner.print_test("Get User's RSVPs")
response = requests.get(f"{BASE_URL}/rsvps/my-rsvps", headers=att_headers)
if runner.assert_status(response, 200, "Get my RSVPs"):
    events = response.json()['data']['events']
    if len(events) > 0:
        print(f"✅ User has RSVP'd to {len(events)} event(s)")
        runner.passed += 1

# Test 18: Cancel RSVP
runner.print_test("Cancel RSVP")
response = requests.delete(f"{BASE_URL}/rsvps/{runner.event_id}", headers=att_headers)
runner.assert_status(response, 200, "Cancel RSVP")

# Test 19: Cancel non-existent RSVP (should fail)
runner.print_test("Cancel Non-existent RSVP (Should Fail)")
response = requests.delete(f"{BASE_URL}/rsvps/{runner.event_id}", headers=att_headers)
runner.assert_status(response, 404, "Should return 404")

# Test 20: Verify RSVP count decreased
runner.print_test("Verify RSVP Count After Cancellation")
response = requests.get(f"{BASE_URL}/events/{runner.event_id}")
if runner.assert_status(response, 200, "Get event"):
    event = response.json()['data']
    if event['rsvp_count'] == 0:
        print("✅ RSVP count correctly updated to 0")
        runner.passed += 1
    else:
        print(f"❌ RSVP count is {event['rsvp_count']}, expected 0")
        runner.failed += 1

# Test 21: Event appears in public list with correct data
runner.print_test("Verify Event in Public List")
response = requests.get(f"{BASE_URL}/events")
if runner.assert_status(response, 200, "Get events"):
    events = response.json()['data']['events']
    event = next((e for e in events if e['id'] == runner.event_id), None)
    if event:
        print(f"✅ Event found with RSVP count: {event['rsvp_count']}")
        print(f"   Title: {event['title']}")
        print(f"   City: {event['city']}")
        print(f"   Category: {event['category']}")
        runner.passed += 1
    else:
        print("❌ Event not found in list")
        runner.failed += 1

# Test 22: Delete event (organizer)
runner.print_test("Delete Event - Organizer")
response = requests.delete(f"{BASE_URL}/events/{runner.event_id}", headers=org_headers)
runner.assert_status(response, 200, "Delete event")

# Test 23: Verify event is canceled (not in public list)
runner.print_test("Verify Event is Canceled")
response = requests.get(f"{BASE_URL}/events/{runner.event_id}")
if response.status_code == 404:
    print("✅ Event is no longer publicly visible")
    runner.passed += 1
else:
    print("❌ Event still visible")
    runner.failed += 1

# Test 24: Organizer can still see their canceled event
runner.print_test("Organizer Views Canceled Event")
response = requests.get(f"{BASE_URL}/events/organizer/my-events", headers=org_headers)
if runner.assert_status(response, 200, "Get organizer events"):
    events = response.json()['data']['events']
    print(f"DEBUG: Found {len(events)} event(s) in organizer's list")
    for event in events:
        print(f"  - Event ID: {event['id']}, Status: {event['status']}, Title: {event['title']}")
    
    canceled_event = next((e for e in events if e['id'] == runner.event_id), None)
    if canceled_event:
        if canceled_event['status'] == 'canceled':
            print("✅ Organizer can see canceled event in their list")
            print(f"   Status: {canceled_event['status']}")
            runner.passed += 1
        else:
            print(f"❌ Event found but status is '{canceled_event['status']}', expected 'canceled'")
            runner.failed += 1
    else:
        print(f"❌ Canceled event (ID: {runner.event_id}) not found in organizer's list")
        runner.failed += 1

# Print summary
runner.print_summary()

if runner.failed == 0:
    print("\n🎉 ALL PHASE 2 MVP TESTS PASSED! 🎉")
    print("Event management and RSVP system working perfectly!")
else:
    print(f"\n⚠️  {runner.failed} test(s) failed. Check the output above.")