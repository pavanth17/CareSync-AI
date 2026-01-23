from app import app, db
from models import Ward, StaffMember, Patient
import logging

logging.basicConfig(level=logging.INFO)

def seed_wards_only():
    with app.app_context():
        try:
            # Standard wards that should always exist
            standard_wards = ['General Ward', 'Emergency', 'ICU', 'Pediatrics', 'Cardiology', 'Neurology', 'Orthopedics', 'Oncology', 'Surgery']
            
            # Seed from existing departments in Patient table
            existing_depts = db.session.query(Patient.department).distinct().filter(Patient.department.isnot(None)).all()
            dept_names = [d[0] for d in existing_depts]
            
            all_wards = set(dept_names + standard_wards)
            
            added_count = 0
            for i, name in enumerate(all_wards):
                if not name: continue
                
                # Check if exists
                if Ward.query.filter_by(name=name).first():
                    continue
                    
                # Assign a random floor
                floor = f"{i % 5 + 1}th Floor"
                
                # Try to find a nurse to assign as head (optional)
                head_nurse = StaffMember.query.filter_by(role='nurse', department=name).first()
                head_nurse_id = head_nurse.id if head_nurse else None
                
                ward = Ward(
                    name=name,
                    capacity=30,
                    floor=floor,
                    head_nurse_id=head_nurse_id
                )
                db.session.add(ward)
                added_count += 1
            
            db.session.commit()
            logging.info(f"Seeded {added_count} new wards.")
            
        except Exception as e:
            logging.error(f"Error seeding wards: {e}")

if __name__ == "__main__":
    seed_wards_only()
