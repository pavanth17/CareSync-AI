import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import app
from models import Patient, StaffMember

with app.app_context():
    discharged = Patient.query.filter_by(status='discharged').all()
    print('Discharged patients:')
    for p in discharged:
        print(f'  {p.patient_id} | name: {p.full_name} | phone: {p.phone} | db id: {p.id}')

    first = Patient.query.order_by(Patient.id).first()
    print('\nFirst DB patient:')
    if first:
        print(f'  db id: {first.id} | pid: {first.patient_id} | name: {first.full_name} | phone: {first.phone}')

    doctors = StaffMember.query.filter_by(role='doctor').limit(5).all()
    print('\nSample doctors:')
    for d in doctors:
        print(f'  {d.staff_id} | {d.full_name} | active: {d.is_active}')

    nurses = StaffMember.query.filter_by(role='nurse').limit(5).all()
    print('\nSample nurses:')
    for n in nurses:
        print(f'  {n.staff_id} | {n.full_name} | active: {n.is_active}')
