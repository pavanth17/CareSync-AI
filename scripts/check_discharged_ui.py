import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from models import Patient

with app.test_client() as client:
    with app.app_context():
        patient = Patient.query.filter_by(status='discharged').first()
        if not patient:
            print('No discharged patient found')
            sys.exit(2)
        with client.session_transaction() as sess:
            sess['discharged_patient_id'] = patient.id
        resp = client.get('/discharged-dashboard')
        html = resp.get_data(as_text=True)
        found_new_chat = 'New Chat' in html or 'bi-chat-dots' in html
        found_book = 'Book' in html or 'calendar-plus' in html
        found_summary = 'Summary' in html or 'bi-info-circle' in html
        print('patient:', patient.patient_id)
        print('status_code:', resp.status_code)
        print('has_new_chat:', found_new_chat)
        print('has_book:', found_book)
        print('has_summary:', found_summary)
        if not (found_new_chat and found_book and found_summary):
            # write html to file for inspection
            out = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tmp_discharged_dashboard.html'))
            with open(out, 'w', encoding='utf-8') as f:
                f.write(html)
            print('Wrote dashboard HTML to', out)
