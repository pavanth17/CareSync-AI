#!/usr/bin/env python3
"""Direct test of template rendering"""

from app import app
from models import Patient
import re

with app.app_context():
    patient = Patient.query.filter_by(status='discharged').first()
    
    if patient:
        print(f"Found patient ID={patient.id}")
        
        from flask import render_template
        html = render_template('discharged_dashboard.html', patient=patient, chat_history=[])
        
        print(f"Rendered: {len(html)} bytes")
        print(f"Has initializeButtonHandlers: {'initializeButtonHandlers' in html}")
        print(f"Has openBookBtn: {'openBookBtn' in html}")
        print(f"Has patientId: {'patientId' in html}")
        
        if '<script>' in html:
            scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
            print(f"Found {len(scripts)} script tags")
            for i, script in enumerate(scripts):
                size = len(script.strip())
                print(f"  Script {i}: {size} chars - {'EMPTY' if size == 0 else 'OK'}")
                if 'function' in script:
                    print(f"    Has functions")
        else:
            print("NO SCRIPT TAG FOUND!")
    else:
        print("No discharged patient found")
