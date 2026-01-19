#!/usr/bin/env python
"""Test login for various doctors and nurses."""

import requests
import sys

BASE_URL = 'http://127.0.0.1:5000'

# Test data: various staff to verify login works
test_staff = [
    ('DOC0001', 'password', 'doctor1'),
    ('DOC0005', 'password', 'doctor5'),
    ('DOC0010', 'password', 'doctor10'),
    ('DOC0020', 'password', 'doctor20'),
    ('NRS0001', 'password', 'nurse1'),
    ('NRS0010', 'password', 'nurse10'),
    ('NRS0030', 'password', 'nurse30'),
    ('NRS0060', 'password', 'nurse60'),
]

def test_login(staff_id, password, label):
    """Test login for a staff member."""
    try:
        session = requests.Session()
        resp = session.post(f'{BASE_URL}/login', data={
            'staff_id': staff_id,
            'password': password
        }, allow_redirects=False)
        
        if resp.status_code == 302:
            # Check if session cookie is set
            if 'Set-Cookie' in resp.headers:
                print(f"✓ {label} ({staff_id}): Login successful, session cookie set")
                return True
            else:
                print(f"✗ {label} ({staff_id}): Redirect but no session cookie")
                return False
        elif resp.status_code == 200:
            # Check for error message in response
            if 'invalid' in resp.text.lower() or 'incorrect' in resp.text.lower():
                print(f"✗ {label} ({staff_id}): Invalid credentials")
                return False
            else:
                print(f"✓ {label} ({staff_id}): Login page returned (may indicate success)")
                return True
        else:
            print(f"✗ {label} ({staff_id}): Unexpected status {resp.status_code}")
            return False
    except Exception as e:
        print(f"✗ {label} ({staff_id}): Error - {e}")
        return False

print("Testing staff login for various doctors and nurses...\n")
passed = 0
for staff_id, password, label in test_staff:
    if test_login(staff_id, password, label):
        passed += 1

print(f"\nResults: {passed}/{len(test_staff)} staff can login")
