from app import app, db
from models import StaffMember
import sys

staff_id = sys.argv[1]
new_pass = sys.argv[2]
with app.app_context():
    s = StaffMember.query.filter_by(staff_id=staff_id).first()
    if not s:
        print("Staff not found:", staff_id); sys.exit(1)
    s.set_password(new_pass)
    db.session.commit()
    print("Password updated for", staff_id)