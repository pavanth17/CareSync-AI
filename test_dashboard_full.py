#!/usr/bin/env python3
"""Test dashboard rendering with correct login"""

from app import app
from models import Patient
import requests

with app.app_context():
    # Get a discharged patient
    patient = Patient.query.filter_by(status='discharged').first()
    
    if not patient:
        print("ERROR: No discharged patient found")
        exit(1)
    
    print(f"Using patient: {patient.patient_id} (phone: {patient.phone})")
    
    # Now login and get dashboard
    session = requests.Session()
    
    # Login
    resp = session.post(
        'http://localhost:5000/discharged-portal',
        data={'patient_id': patient.patient_id, 'phone': patient.phone},
        allow_redirects=True
    )
    print(f"Login: {resp.status_code} (URL: {resp.url})")
    
    # Get dashboard
    resp2 = session.get('http://localhost:5000/discharged-dashboard')
    print(f"Dashboard: {resp2.status_code} ({len(resp2.text)} bytes)")
    
    # Check content
    tests = {
        'initializeButtonHandlers': 'Main handler function',
        'openBookBtn': 'Book button ID',
        '<script>': 'Script tag',
        'function addMessage': 'addMessage function',
    }
    
    print("\nContent checks:")
    for pattern, desc in tests.items():
        found = pattern in resp2.text
        status = "[OK]" if found else "[FAIL]"
        print(f"  {status} {desc}")
    
    # Save for manual inspection
    with open('dashboard_test.html', 'w', encoding='utf-8') as f:
        f.write(resp2.text)
    print("\nSaved to dashboard_test.html")
