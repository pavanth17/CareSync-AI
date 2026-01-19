#!/usr/bin/env python3
"""Test that the Book button fix is working"""

import requests

BASE_URL = "http://localhost:5000"

print("=" * 60)
print("TESTING BOOK BUTTON FIX")
print("=" * 60)

session = requests.Session()

# Login
print("\n[1] Logging in...")
session.post(f"{BASE_URL}/login-discharged", 
             data={'patient_id': 'PAT000001', 'password': 'password'})

# Get dashboard
print("[2] Fetching dashboard...")
resp = session.get(f"{BASE_URL}/discharged-dashboard")
html = resp.text

print(f"Status: {resp.status_code}")
print(f"Size: {len(html)} bytes")

# Check for key patterns
checks = {
    'initializeButtonHandlers': 'Main handler function',
    'attachBookingFormHandler': 'Form handler function',
    'Initializing button handlers': 'Console log message',
    'openBookBtn.addEventListener': 'Book button click handler',
    'new bootstrap.Modal': 'Bootstrap modal initialization',
    'document.addEventListener(\'click\'': 'Emergency fallback handler',
    'document.addEventListener(\'DOMContentLoaded\'': 'DOMContentLoaded listener',
    'window.addEventListener(\'load\', initializeButtonHandlers)': 'Window load listener',
}

print("\n" + "=" * 60)
print("CHECKING FOR KEY PATTERNS")
print("=" * 60)

passed = 0
failed = 0

for pattern, description in checks.items():
    if pattern in html:
        print(f"[OK] {description}")
        passed += 1
    else:
        print(f"[FAIL] {description}")
        failed += 1

print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed")
print("=" * 60)

if failed == 0:
    print("\n✓ All checks passed!")
    print("\nNEXT STEPS:")
    print("1. Go to http://localhost:5000/discharged-portal")
    print("2. Login: patient_id = PAT000001, password = password")
    print("3. Click the 'Book' button on the chat page")
    print("4. Open DevTools (F12) and check Console for messages")
    print("5. Modal should appear when you click Book")
else:
    print(f"\n✗ {failed} checks failed!")
