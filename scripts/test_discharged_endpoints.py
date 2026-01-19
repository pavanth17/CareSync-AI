import json
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from models import Patient

with app.test_client() as client:
    with app.app_context():
        # pick one discharged patient
        patient = Patient.query.filter_by(status='discharged').first()
        if not patient:
            print('No discharged patient found')
            sys.exit(1)
        # set session key
        with client.session_transaction() as sess:
            sess['discharged_patient_id'] = patient.id
        print('Testing for patient:', patient.patient_id)

        # Clear history
        resp = client.post('/api/discharged/clear-history')
        print('clear-history', resp.status_code, resp.get_json())

        # Book appointment
        resp = client.post('/api/discharged/book-appointment', json={'preferred_date': None, 'preferred_time': '10:00', 'notes': 'Test appt'})
        print('book-appointment', resp.status_code, resp.get_json())

        # Summary
        resp = client.get('/api/discharged/summary')
        print('summary', resp.status_code)
        try:
            print(json.dumps(resp.get_json(), indent=2))
        except Exception:
            print('no json')

        # Chat (fallback path if gemini not configured)
        resp = client.post('/api/discharged/chat', json={'message': 'Hello, test', 'language': 'en'})
        print('chat', resp.status_code, resp.get_json())
