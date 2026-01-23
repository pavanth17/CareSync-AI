"""Initialize fresh database with synthetic data and a test discharged patient for chat testing.

This script supports command-line flags so you can generate custom demo counts without editing source files.
"""

import os
import time
import argparse
from app import app, db
from models import Patient
from synthetic_data import initialize_synthetic_data


def main(args):
    # Ensure we're in app context
    with app.app_context():
        # Optionally delete DB file first
        db_path = 'patient_care_dev.db'
        if args.delete_db and os.path.exists(db_path):
            # Wait a moment for any locks to release
            time.sleep(1)
            try:
                os.remove(db_path)
                print(f"✓ Deleted existing database: {db_path}")
            except Exception as e:
                print(f"⚠ Could not delete database: {e}")
                print("  Attempting to work with existing database...")

        # Drop existing tables (safe when file is locked) and recreate tables from models
        try:
            db.drop_all()
            print(f"[OK] Dropped existing database tables")
        except Exception:
            pass

        db.create_all()
        print(f"[OK] Created all database tables")

        # Generate synthetic data with requested demo counts
        initialize_synthetic_data(
            num_doctors=args.doctors,
            num_nurses=args.nurses,
            num_patients=args.patients,
            num_discharged=args.discharged
        )
        print(f"[OK] Generated synthetic data ({args.doctors} doctors, {args.nurses} nurses, {args.patients} patients; {args.discharged} discharged)")

        # Print one example discharged patient for quick testing
        discharged_example = Patient.query.filter_by(status='discharged').first()
        if discharged_example:
            print(f"✓ Example discharged patient: {discharged_example.patient_id} ({discharged_example.first_name} {discharged_example.last_name})")
            print(f"  Phone: {discharged_example.phone}")
            print(f"  Use these credentials to test the discharged portal:")
            print(f"    Patient ID: {discharged_example.patient_id}")
            print(f"    Phone: {discharged_example.phone}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Initialize demo database with synthetic data')
    parser.add_argument('--doctors', type=int, default=30, help='Number of doctor accounts to create')
    parser.add_argument('--nurses', type=int, default=60, help='Number of nurse accounts to create')
    parser.add_argument('--patients', type=int, default=70, help='Number of patient records to create')
    parser.add_argument('--discharged', type=int, default=20, help='Number of patients to mark discharged')
    parser.add_argument('--delete-db', dest='delete_db', action='store_true', help='Delete the sqlite DB file before initializing')
    parser.set_defaults(delete_db=False)
    args = parser.parse_args()

    main(args)
    
    # Verify ChatMessage table was created
    with app.app_context():
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        if 'chat_messages' in tables:
            print(f"✓ ChatMessage table created successfully")
        else:
            print(f"⚠ ChatMessage table NOT found. Tables: {tables}")

print("\n✓ Database initialization complete!")
print("\nTo test the discharged portal:")
print("1. Start the Flask app: python main.py")
print("2. Navigate to: http://localhost:5000/discharged-portal")
print("3. Set GEMINI_API_KEY environment variable: $env:GEMINI_API_KEY = 'AIzaSyBAx8ZQGwIyimOKfrXdk7hL61kXxHQWagg'")
