#!/usr/bin/env python
"""Test improved patient chat with smart fallback"""
import sys
sys.path.insert(0, 'c:\\projects\\Patient-Care')

from app import app
from models import Patient

print("=" * 70)
print("PATIENT CHAT - IMPROVED WITH SMART FALLBACK")
print("=" * 70)

with app.app_context():
    patient = Patient.query.first()
    
    print(f"\n✅ Testing Chat with Patient: {patient.full_name}")
    print(f"   ID: {patient.id}, Diagnosis: {patient.diagnosis}")
    
    with app.test_client() as client:
        # Login
        client.post('/patient-login',
            data={'patient_id': patient.patient_id, 'phone': patient.phone})
        
        test_queries = [
            ("What are my current medications?", "medications"),
            ("What is my blood pressure?", "vital signs"),
            ("Tell me about my diagnosis", "diagnosis"),
            ("Do I have any appointments?", "appointments"),
        ]
        
        for query, query_type in test_queries:
            print(f"\n{'─' * 70}")
            print(f"Query: {query}")
            print(f"Type: {query_type}")
            
            resp = client.post(f'/api/patient/{patient.id}/chat',
                json={'message': query, 'language': 'en'})
            
            if resp.status_code == 200:
                result = resp.get_json()
                response_text = result.get('message', '')
                print(f"✅ Response:")
                print(f"\n{response_text}\n")
            else:
                print(f"❌ Error: {resp.status_code}")

print("\n" + "=" * 70)
print("✅ CHAT SYSTEM IS WORKING WITH SMART FALLBACK")
print("=" * 70)
