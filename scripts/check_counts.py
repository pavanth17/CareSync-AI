import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from models import StaffMember, Patient

with app.app_context():
    print('staff_count=', StaffMember.query.count())
    print('doctors=', StaffMember.query.filter_by(role='doctor').count())
    print('nurses=', StaffMember.query.filter_by(role='nurse').count())
    print('patients=', Patient.query.count())
    print('discharged=', Patient.query.filter_by(status='discharged').count())
