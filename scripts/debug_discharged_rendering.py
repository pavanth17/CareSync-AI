#!/usr/bin/env python
"""Debug discharged dashboard rendering."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import Patient

with app.test_client() as client:
    with app.app_context():
        patient = Patient.query.filter_by(status='discharged').first()
        if not patient:
            print('ERROR: No discharged patient')
            sys.exit(1)

        with client.session_transaction() as sess:
            sess['discharged_patient_id'] = patient.id

        resp = client.get('/discharged-dashboard')
        html = resp.get_data(as_text=True)
        
        # Find the patient.id references in JS
        import re
        
        print(f"Patient ID from DB: {patient.id}")
        print(f"Patient object has id: {hasattr(patient, 'id')}")
        
        # Check what patient.id is rendered as in HTML
        matches = re.findall(r'/api/patient/(\d+)/', html)
        if matches:
            print(f"\nAPI patient IDs found in HTML: {set(matches)}")
        else:
            print("\nERROR: No API patient IDs found in HTML!")
            
        # Look for template variable rendering
        if '{{ patient.id }}' in html:
            print("\nERROR: Template variable {{ patient.id }} was NOT rendered!")
        elif f'/api/patient/{patient.id}/' in html:
            print(f"\n✓ Patient ID {patient.id} is correctly rendered in API calls")
        else:
            print(f"\nERROR: Patient ID {patient.id} not found in expected format")
            
        # Check button IDs
        if 'id="newChatBtn"' in html and 'id="openBookBtn"' in html and 'id="summaryBtn"' in html:
            print("✓ All button IDs present")
        else:
            print("✗ Some button IDs missing")
