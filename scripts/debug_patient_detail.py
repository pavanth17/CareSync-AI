import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import app
from models import StaffMember, Patient

with app.app_context():
    staff = StaffMember.query.filter_by(staff_id='DOC0001').first()
    print('Using staff:', staff.staff_id, staff.full_name)

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['staff_id'] = staff.id
        sess['staff_role'] = staff.role

    resp = client.get('/patient/1')
    print('status_code:', resp.status_code)
    print(resp.get_data(as_text=True)[:1000])
