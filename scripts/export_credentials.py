import csv
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from models import StaffMember, Patient

OUT_CSV = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'DEMO_CREDENTIALS.csv'))

with app.app_context():
    admins = StaffMember.query.filter_by(role='admin', is_active=True).all()
    doctors = StaffMember.query.filter_by(role='doctor', is_active=True).all()
    nurses = StaffMember.query.filter_by(role='nurse', is_active=True).all()
    patients = Patient.query.filter_by(status='discharged').all()

    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['type', 'id', 'name', 'email_or_phone', 'password_hint'])

        for a in admins:
            writer.writerow(['admin', a.staff_id, a.full_name, a.email or '', 'admin123'])

        for i, d in enumerate(doctors, 1):
            writer.writerow(['doctor', d.staff_id, d.full_name, d.email or '', f'doctor{i}'])

        for i, n in enumerate(nurses, 1):
            writer.writerow(['nurse', n.staff_id, n.full_name, n.email or '', f'nurse{i}'])

        for p in patients:
            writer.writerow(['patient', p.patient_id, p.full_name, p.phone or p.email or '', 'Use Patient ID + Phone'])

    print('Exported credentials to', OUT_CSV)
