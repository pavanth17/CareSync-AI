#!/usr/bin/env python3
"""Test with no-cache headers"""

from app import app
from models import Patient
import requests

with app.app_context():
    patient = Patient.query.filter_by(status='discharged').first()
    
    session = requests.Session()
    
    # Add no-cache headers
    session.headers.update({
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    })
    
    # Login
    session.post('http://localhost:5000/discharged-portal',
                 data={'patient_id': patient.patient_id, 'phone': patient.phone})
    
    # Get dashboard with no-cache
    resp = session.get('http://localhost:5000/discharged-dashboard')
    
    print(f"Response size: {len(resp.text)} bytes")
    
    # Check for new and old patterns
    has_new = 'initializeButtonHandlers' in resp.text
    has_old_window = "window.addEventListener('load'" in resp.text
    has_old_function_name = "window.addEventListener('load', function()" in resp.text
    
    print(f"Has new 'initializeButtonHandlers': {has_new}")
    print(f"Has old 'window.addEventListener' pattern: {has_old_window}")
    print(f"Has old function call pattern: {has_old_function_name}")
    
    # Print the actual pattern found
    import re
    match = re.search(r"window\.addEventListener\('load'[^}]*?\)", resp.text)
    if match:
        print(f"\nFound old pattern at: {match.group(0)[:100]}...")
