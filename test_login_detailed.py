"""
Comprehensive test of patient login functionality
"""
import sys
import requests
import time
from app import db, app
from models import Patient

# First, check database state
print("=" * 60)
print("DATABASE STATE CHECK")
print("=" * 60)

app.app_context().push()
patients = Patient.query.limit(5).all()
print(f"Total patients in database: {Patient.query.count()}")
print("\nFirst 5 patients:")
for p in patients:
    print(f"  ID: {p.id}, Patient ID: {p.patient_id}, Name: {p.first_name} {p.last_name}, Phone: {p.phone}")

# Now test the web endpoint
print("\n" + "=" * 60)
print("WEB ENDPOINT TEST")
print("=" * 60)

time.sleep(1)  # Give Flask time to be ready

url = 'http://localhost:5000/patient-login'
data = {
    'patient_id': 'PAT000001',
    'phone': '555-935-4604'
}

print(f"\nAttempting login with:")
print(f"  Patient ID: {data['patient_id']}")
print(f"  Phone: {data['phone']}")

try:
    response = requests.post(url, data=data, allow_redirects=False, timeout=5)
    print(f"\n✓ Request successful!")
    print(f"  Status Code: {response.status_code}")
    print(f"  Location Header: {response.headers.get('Location', 'N/A')}")
    
    # Check for flash messages in response
    if 'Welcome back' in response.text:
        print("  ✓ Welcome message found in response - LOGIN SUCCESSFUL")
    elif 'Invalid Patient ID' in response.text:
        print("  ✗ Invalid Patient ID message found - WRONG CREDENTIALS")
    else:
        print("  ? No clear message in response")
        
except requests.exceptions.ConnectionError as e:
    print(f"✗ Connection Error: {e}")
    print("Flask server may not be running")
except requests.exceptions.Timeout as e:
    print(f"✗ Timeout Error: {e}")
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")

print("\n" + "=" * 60)
