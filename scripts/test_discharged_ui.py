#!/usr/bin/env python
"""Test discharged dashboard has the buttons and correct endpoints."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import Patient

with app.test_client() as client:
    with app.app_context():
        # Get a discharged patient
        patient = Patient.query.filter_by(status='discharged').first()
        if not patient:
            print('ERROR: No discharged patient found')
            sys.exit(1)

        # Set discharged session
        with client.session_transaction() as sess:
            sess['discharged_patient_id'] = patient.id

        print(f"Testing discharged dashboard for patient: {patient.patient_id}")
        
        # Fetch dashboard HTML
        resp = client.get('/discharged-dashboard')
        html = resp.get_data(as_text=True)
        
        print(f"\nStatus Code: {resp.status_code}")
        
        # Check for button IDs
        checks = {
            'newChatBtn': 'id="newChatBtn"' in html,
            'openBookBtn': 'id="openBookBtn"' in html,
            'summaryBtn': 'id="summaryBtn"' in html,
        }
        
        print("\nButton presence in HTML:")
        for btn, found in checks.items():
            status = "✓" if found else "✗"
            print(f"  {status} {btn}: {found}")
        
        # Check for API endpoint calls in JS
        endpoints = {
            '/api/patient/': '/api/patient/' in html,
            'clear-history': '/api/patient/' in html and 'clear-history' in html,
            'book-appointment': '/api/patient/' in html and 'book-appointment' in html,
            'summary': '/api/patient/' in html and '/summary' in html,
        }
        
        print("\nAPI endpoint calls in JS:")
        for ep, found in endpoints.items():
            status = "✓" if found else "✗"
            print(f"  {status} {ep}: {found}")
        
        all_ok = all(checks.values()) and all(endpoints.values())
        if all_ok:
            print("\n✓ All checks passed!")
        else:
            print("\n✗ Some checks failed!")
            sys.exit(1)
