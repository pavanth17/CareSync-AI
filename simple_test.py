#!/usr/bin/env python3
"""
Simple test of discharged patient portal with Gemini AI chat.
"""
import requests
import json
import time

BASE_URL = "http://localhost:5000"
TEST_PATIENT_ID = "PAT001"
TEST_PHONE = "5556667777"

print("=" * 70)
print("CareSync AI Assistant - Discharged Patient Portal Test")
print("=" * 70)

# Test 1: Try home page to verify Flask is up
print("\n[1] Checking if Flask is running...")
try:
    resp = requests.get(f"{BASE_URL}/", timeout=5)
    print(f"    OK - Flask is running (status: {resp.status_code})")
except Exception as e:
    print(f"    FAIL - Flask not responding: {e}")
    exit(1)

# Test 2: GET discharged portal login form
print("\n[2] GET /discharged-portal (login form)...")
try:
    resp = requests.get(f"{BASE_URL}/discharged-portal", timeout=5)
    if resp.status_code == 200:
        print(f"    OK - Loaded successfully")
        if "Patient ID" in resp.text or "phone" in resp.text.lower():
            print(f"    OK - Login form contains expected fields")
    else:
        print(f"    FAIL - Status {resp.status_code}")
except Exception as e:
    print(f"    FAIL - {e}")

# Test 3: POST login with correct credentials
print("\n[3] POST /discharged-portal (login attempt)...")
try:
    session = requests.Session()
    resp = session.post(
        f"{BASE_URL}/discharged-portal",
        data={"patient_id": TEST_PATIENT_ID, "phone": TEST_PHONE},
        allow_redirects=False,
        timeout=5
    )
    print(f"    Status: {resp.status_code}")
    if resp.status_code in [200, 302]:
        print(f"    OK - Login processed")
        if resp.status_code == 302 and 'Location' in resp.headers:
            print(f"    Redirect to: {resp.headers['Location']}")
    else:
        print(f"    FAIL - Unexpected status")
except Exception as e:
    print(f"    FAIL - {e}")

# Test 4: GET dashboard after login
print("\n[4] GET /discharged-dashboard (chat interface)...")
try:
    session = requests.Session()
    session.post(
        f"{BASE_URL}/discharged-portal",
        data={"patient_id": TEST_PATIENT_ID, "phone": TEST_PHONE},
        timeout=5
    )
    resp = session.get(f"{BASE_URL}/discharged-dashboard", timeout=5)
    if resp.status_code == 200:
        print(f"    OK - Dashboard loaded")
        if "CareSync" in resp.text or "message" in resp.text.lower():
            print(f"    OK - Dashboard contains chat UI")
    else:
        print(f"    Status: {resp.status_code}")
except Exception as e:
    print(f"    FAIL - {e}")

# Test 5: POST chat message (real Gemini call with API key)
print("\n[5] POST /api/discharged/chat (Gemini AI response)...")
try:
    session = requests.Session()
    session.post(
        f"{BASE_URL}/discharged-portal",
        data={"patient_id": TEST_PATIENT_ID, "phone": TEST_PHONE},
        timeout=5
    )
    
    chat_resp = session.post(
        f"{BASE_URL}/api/discharged/chat",
        json={"message": "Hello, how are you today?", "language": "en"},
        timeout=10
    )
    
    if chat_resp.status_code == 200:
        try:
            data = chat_resp.json()
            print(f"    OK - Received response")
            if 'message' in data:
                msg = data['message']
                print(f"    AI Response: {msg[:150]}...")
            elif 'error' in data:
                print(f"    Error from API: {data['error']}")
        except json.JSONDecodeError:
            print(f"    FAIL - Invalid JSON response")
    else:
        print(f"    Status: {chat_resp.status_code}")
        print(f"    Response: {chat_resp.text[:200]}")
except Exception as e:
    print(f"    FAIL - {e}")

print("\n" + "=" * 70)
print("Test complete!")
print("=" * 70)
