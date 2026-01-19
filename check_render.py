#!/usr/bin/env python3
"""Check what Flask is actually rendering"""

from app import app
from models import Patient
import requests

print("=== Flask Template Rendering Test ===\n")

with app.app_context():
    patient = Patient.query.filter_by(status='discharged').first()
    
    print(f"Patient: {patient.patient_id}")
    
    # Try rendering the template directly
    from flask import render_template
    try:
        html = render_template('discharged_dashboard.html', patient=patient, chat_history=[])
        print(f"Direct render: {len(html)} bytes")
        
        # Check for both old and new code
        has_new = 'initializeButtonHandlers' in html
        has_old_pattern = "window.addEventListener('load'" in html
        
        print(f"  Has initializeButtonHandlers: {has_new}")
        print(f"  Has old pattern: {has_old_pattern}")
        
        # Save for inspection
        with open('direct_render.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"  Saved to direct_render.html")
        
    except Exception as e:
        print(f"ERROR rendering: {e}")
    
    print("\n=== Via HTTP Request ===\n")
    
    session = requests.Session()
    session.post('http://localhost:5000/discharged-portal',
                 data={'patient_id': patient.patient_id, 'phone': patient.phone})
    resp = session.get('http://localhost:5000/discharged-dashboard')
    
    print(f"HTTP response: {resp.status_code}, {len(resp.text)} bytes")
    print(f"  Has initializeButtonHandlers: {'initializeButtonHandlers' in resp.text}")
    old_pattern = "window.addEventListener('load'" 
    print(f"  Has old pattern: {old_pattern in resp.text}")
