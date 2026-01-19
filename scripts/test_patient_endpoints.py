import json
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from models import Patient, StaffMember

with app.test_client() as client:
    with app.app_context():
        patient = Patient.query.first()
        if not patient:
            print('No patient found')
            sys.exit(1)

        # pick a staff member (doctor or nurse) to simulate logged-in staff
        staff = StaffMember.query.filter_by(is_active=True).first()
        if not staff:
            print('No staff member found')
            sys.exit(1)

        with client.session_transaction() as sess:
            sess['staff_id'] = staff.id
            sess['staff_role'] = staff.role

        print('Testing patient endpoints for patient:', patient.patient_id, 'as staff:', staff.staff_id)

        # Clear history
        resp = client.post(f'/api/patient/{patient.id}/clear-history')
        print('clear-history', resp.status_code, resp.get_json())

        # Book appointment
        resp = client.post(f'/api/patient/{patient.id}/book-appointment', json={'preferred_date': None, 'preferred_time': '11:00', 'notes': 'Staff test appt'})
        print('book-appointment', resp.status_code, resp.get_json())

        # Summary
        resp = client.get(f'/api/patient/{patient.id}/summary')
        print('summary', resp.status_code)
        try:
            print(json.dumps(resp.get_json(), indent=2))
        except Exception:
            print('no json')

        # Chat (fallback if no gemini key)
        resp = client.post(f'/api/patient/{patient.id}/chat', json={'message': 'Hello from staff test', 'language': 'en'})
        print('chat', resp.status_code, resp.get_json())
