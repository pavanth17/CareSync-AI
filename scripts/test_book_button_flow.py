#!/usr/bin/env python
"""Test book button click flow."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import Patient
import json

with app.test_client() as client:
    with app.app_context():
        p = Patient.query.filter_by(status='discharged').first()
        if not p:
            print("ERROR: No discharged patient found")
            sys.exit(1)
            
        with client.session_transaction() as sess:
            sess['discharged_patient_id'] = p.id
        
        print(f"Testing Book button for patient: {p.patient_id} (ID: {p.id})")
        
        # Step 1: Get the dashboard and check if button exists
        resp = client.get('/discharged-dashboard')
        html = resp.get_data(as_text=True)
        
        print(f"\n1. Dashboard Status: {resp.status_code}")
        if 'id="openBookBtn"' in html:
            print("   ✓ Book button found in HTML")
        else:
            print("   ✗ Book button NOT found in HTML")
            
        if 'id="bookModal"' in html:
            print("   ✓ Book modal found in HTML")
        else:
            print("   ✗ Book modal NOT found in HTML")
            
        if 'id="appointmentIssue"' in html:
            print("   ✓ Appointment Issue field found")
        else:
            print("   ✗ Appointment Issue field NOT found")
        
        # Step 2: Test the booking API directly
        print(f"\n2. Testing Book Appointment API:")
        from datetime import datetime, timedelta
        tomorrow = (datetime.now() + timedelta(days=1)).isoformat()
        
        resp = client.post(
            f'/api/patient/{p.id}/book-appointment',
            json={
                'preferred_date': tomorrow,
                'preferred_time': '15:30',
                'notes': 'I have a stomach ache and need medication advice'
            }
        )
        
        print(f"   Status: {resp.status_code}")
        data = resp.get_json()
        if resp.status_code == 201:
            print(f"   ✓ Appointment created: ID {data['appointment_id']}")
            print(f"   ✓ Status: {data['status']}")
        else:
            print(f"   ✗ Error: {data.get('error', 'Unknown error')}")
        
        # Step 3: Check event listeners in JS
        print(f"\n3. JavaScript Event Listeners:")
        if 'addEventListener' in html and 'openBookBtn' in html:
            print("   ✓ openBookBtn event listener code found")
        else:
            print("   ✗ openBookBtn event listener code NOT found")
            
        if 'submitBooking' in html and 'addEventListener' in html:
            print("   ✓ submitBooking event listener code found")
        else:
            print("   ✗ submitBooking event listener code NOT found")
