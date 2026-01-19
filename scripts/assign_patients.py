import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from models import Patient, StaffMember
import random

with app.app_context():
    patients = Patient.query.filter(Patient.status != 'discharged').all()
    doctors = StaffMember.query.filter_by(role='doctor', is_active=True).all()
    nurses = StaffMember.query.filter_by(role='nurse', is_active=True).all()

    unassigned_docs = [p for p in patients if not p.assigned_doctor_id]
    unassigned_nurses = [p for p in patients if not p.assigned_nurse_id]

    print(f"Total patients (non-discharged): {len(patients)}")
    print(f"Unassigned doctors: {len(unassigned_docs)}")
    print(f"Unassigned nurses: {len(unassigned_nurses)}")
    print(f"Available doctors: {len(doctors)}")
    print(f"Available nurses: {len(nurses)}")

    # Assign unassigned patients to doctors
    if unassigned_docs and doctors:
        for p in unassigned_docs:
            p.assigned_doctor_id = random.choice(doctors).id
        print(f"✓ Assigned {len(unassigned_docs)} patients to doctors")

    # Assign unassigned patients to nurses
    if unassigned_nurses and nurses:
        for p in unassigned_nurses:
            p.assigned_nurse_id = random.choice(nurses).id
        print(f"✓ Assigned {len(unassigned_nurses)} patients to nurses")

    # Mark some staff as on-duty for better demo visibility
    on_duty_count = max(3, len(doctors) // 5)  # ~20% on duty
    doctors_to_mark = random.sample(doctors, on_duty_count)
    for d in doctors_to_mark:
        d.is_on_duty = True
    print(f"✓ Marked {on_duty_count} doctors as on-duty")

    on_duty_count = max(5, len(nurses) // 5)  # ~20% on duty
    nurses_to_mark = random.sample(nurses, on_duty_count)
    for n in nurses_to_mark:
        n.is_on_duty = True
    print(f"✓ Marked {on_duty_count} nurses as on-duty")

    from datetime import datetime
    from models import Shift
    # Create shifts for on-duty staff
    for d in doctors_to_mark:
        shift = Shift(
            staff_id=d.id,
            shift_type='morning',
            start_time=datetime.now(),
            end_time=datetime.now(),
            department=d.department,
            is_active=True
        )
    for n in nurses_to_mark:
        shift = Shift(
            staff_id=n.id,
            shift_type='morning',
            start_time=datetime.now(),
            end_time=datetime.now(),
            department=n.department,
            is_active=True
        )

    from models import db
    db.session.commit()
    print("✓ All assignments saved to database")
