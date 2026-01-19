#!/usr/bin/env python
"""Test doctor and nurse dashboards see assigned patients."""

import requests

BASE_URL = 'http://127.0.0.1:5000'

def test_dashboard(staff_id, password, role):
    """Test that dashboard shows assigned patients."""
    try:
        session = requests.Session()
        
        # Login
        resp = session.post(f'{BASE_URL}/login', data={
            'staff_id': staff_id,
            'password': password
        }, allow_redirects=True)
        
        # Access dashboard
        dashboard_url = f'{BASE_URL}/{role}'
        resp = session.get(dashboard_url)
        
        if resp.status_code != 200:
            print(f"✗ {role.upper()} {staff_id}: Dashboard returned {resp.status_code}")
            return False
        
        # Check if patient data is in response
        if 'patient' in resp.text.lower() and 'PAT' in resp.text:
            patient_count = resp.text.count('<tr')  # Count table rows
            print(f"✓ {role.upper()} {staff_id}: Dashboard loaded with patient data ({patient_count} rows)")
            return True
        else:
            print(f"✗ {role.upper()} {staff_id}: Dashboard loaded but no patients found")
            return False
                
    except Exception as e:
        print(f"✗ {role.upper()} {staff_id}: Error - {e}")
        return False

print("Testing doctor and nurse dashboards with assigned patients...\n")

test_cases = [
    ('DOC0001', 'password', 'doctor', 'Doctor 1'),
    ('DOC0010', 'password', 'doctor', 'Doctor 10'),
    ('NRS0001', 'password', 'nurse', 'Nurse 1'),
    ('NRS0030', 'password', 'nurse', 'Nurse 30'),
]

passed = 0
for staff_id, password, role, label in test_cases:
    if test_dashboard(staff_id, password, role):
        passed += 1

print(f"\nResults: {passed}/{len(test_cases)} dashboards working")
