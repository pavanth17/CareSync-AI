#!/usr/bin/env python3
from app import app
from models import Patient
import requests

with app.app_context():
    patient = Patient.query.filter_by(status='discharged').first()
    
    session = requests.Session()
    session.post('http://localhost:5000/discharged-portal',
                 data={'patient_id': patient.patient_id, 'phone': patient.phone})
    resp = session.get('http://localhost:5000/discharged-dashboard')
    
    checks = {
        'initializeButtonHandlers': False,
        'DOMContentLoaded': False,
        'attachBookingFormHandler': False,
        'emergency fallback': False,
    }
    
    for key in checks:
        checks[key] = key in resp.text
    
    print(f"Dashboard size: {len(resp.text)} bytes")
    for check, found in checks.items():
        print(f"  {check}: {'YES' if found else 'NO'}")
