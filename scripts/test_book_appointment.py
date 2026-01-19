#!/usr/bin/env python
"""Test booking endpoint with issue field."""
import sys
import os
import json
from datetime import datetime, timedelta
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import Patient, AppointmentRequest

with app.test_client() as client:
    with app.app_context():
        p = Patient.query.filter_by(status='discharged').first()
        with client.session_transaction() as sess:
            sess['discharged_patient_id'] = p.id
        
        # Test booking
        tomorrow = (datetime.now() + timedelta(days=1)).isoformat()
        resp = client.post(
            f'/api/patient/{p.id}/book-appointment',
            json={
                'preferred_date': tomorrow,
                'preferred_time': '14:00',
                'notes': 'I have been experiencing chest pain and shortness of breath'
            }
        )
        
        print(f"Status: {resp.status_code}")
        data = resp.get_json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if resp.status_code == 201:
            appt = AppointmentRequest.query.get(data['appointment_id'])
            if appt:
                print(f"\n✓ Appointment created successfully")
                print(f"  - ID: {appt.id}")
                print(f"  - Date: {appt.preferred_date}")
                print(f"  - Time: {appt.preferred_time}")
                print(f"  - Issue: {appt.notes}")
                print(f"  - Status: {appt.status}")
