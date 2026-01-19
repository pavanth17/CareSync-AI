#!/usr/bin/env python
"""Check if patientId is properly set."""
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
        
        # Check for patientId assignment
        if 'let patientId = ' in html:
            import re
            match = re.search(r'let patientId = (\d+)', html)
            if match:
                print(f"✓ patientId set to: {match.group(1)}")
        
        # Check for fetch calls with patientId template literal
        if '/api/patient/${patientId}' in html:
            print("✓ Fetch calls use ${patientId} template literal")
        else:
            print("✗ Fetch calls don't use template literal format")
            
        # Count button handlers
        handlers = html.count('addEventListener')
        print(f"✓ Found {handlers} event listeners")
