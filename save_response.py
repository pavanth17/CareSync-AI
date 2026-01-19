#!/usr/bin/env python3
"""Capture raw HTTP response"""

from app import app
from models import Patient
import requests

with app.app_context():
    patient = Patient.query.filter_by(status='discharged').first()
    
    session = requests.Session()
    session.post('http://localhost:5000/discharged-portal',
                 data={'patient_id': patient.patient_id, 'phone': patient.phone})
    resp = session.get('http://localhost:5000/discharged-dashboard')
    
    # Save raw response
    with open('raw_response.txt', 'w', encoding='utf-8') as f:
        f.write(resp.text)
    
    print(f"Saved {len(resp.text)} bytes")
    
    # Check for the old  and new patterns
    lines = resp.text.split('\n')
    for i, line in enumerate(lines):
        if 'window.addEventListener' in line or 'initializeButtonHandlers' in line:
            print(f"Line {i+1}: {line.strip()[:100]}")
