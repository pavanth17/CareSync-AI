import requests
import json

s = requests.Session()

# Step 1: POST to login
print("Step 1: POST /discharged-portal")
resp = s.post('http://127.0.0.1:5000/discharged-portal', 
    data={'patient_id': 'PAT001', 'phone': '5556667777'}, 
    timeout=5, 
    allow_redirects=False)
print(f"  Status: {resp.status_code}")
print(f"  Set-Cookie header: {resp.headers.get('Set-Cookie', 'None')}")
print(f"  Cookies in session: {s.cookies}")

# Step 2: GET dashboard (should follow redirect)
print("\nStep 2: GET /discharged-dashboard")
resp2 = s.get('http://127.0.0.1:5000/discharged-dashboard', timeout=5, allow_redirects=False)
print(f"  Status: {resp2.status_code}")
print(f"  Cookies sent: {s.cookies}")
if resp2.status_code >= 400:
    print(f"  First 500 chars: {resp2.text[:500]}")
