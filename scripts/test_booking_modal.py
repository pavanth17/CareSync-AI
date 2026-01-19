#!/usr/bin/env python
"""Verify booking modal updates."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import Patient

with app.test_client() as client:
    with app.app_context():
        p = Patient.query.filter_by(status='discharged').first()
        with client.session_transaction() as sess:
            sess['discharged_patient_id'] = p.id
        
        r = client.get('/discharged-dashboard')
        html = r.get_data(as_text=True)
        
        print(f"Status: {r.status_code}")
        print(f"✓ Has bookSuccessModal: {'bookSuccessModal' in html}")
        print(f"✓ Has appointmentIssue: {'appointmentIssue' in html}")
        print(f"✓ Has submitBooking handler: {'submitBooking' in html}")
        print(f"✓ Issue field label: {'Issue / Reason for Visit' in html}")
        print(f"✓ Success modal header: {'Appointment Confirmed' in html}")
