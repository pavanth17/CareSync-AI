#!/usr/bin/env python3
"""Test verification script for Patient-Care system."""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "http://127.0.0.1:5000"
session = requests.Session()
retry = Retry(connect=3, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)

def test_doctor_login():
    try:
        resp = session.post(f"{BASE_URL}/login", data={"staff_id": "DOC0001", "password": "password"}, timeout=10)
        if resp.status_code == 200:
            resp2 = session.get(f"{BASE_URL}/doctor", timeout=10)
            return resp2.status_code == 200 and "patient" in resp2.text.lower()
    except Exception as e:
        print(f"Doctor test error: {e}")
    return False

def test_nurse_login():
    try:
        resp = session.post(f"{BASE_URL}/login", data={"staff_id": "NRS0001", "password": "password"}, timeout=10)
        if resp.status_code == 200:
            resp2 = session.get(f"{BASE_URL}/nurse", timeout=10)
            return resp2.status_code == 200
    except Exception as e:
        print(f"Nurse test error: {e}")
    return False

def test_discharged_login():
    try:
        resp = session.post(f"{BASE_URL}/discharged-portal", data={"patient_id": "PATDIS001", "phone": "555-0101"}, timeout=10, allow_redirects=True)
        return resp.status_code == 200 and "CareSync" in resp.text
    except Exception as e:
        print(f"Discharged login error: {e}")
    return False

def test_ai_summary():
    try:
        session.post(f"{BASE_URL}/discharged-portal", data={"patient_id": "PATDIS001", "phone": "555-0101"}, timeout=10)
        resp = session.get(f"{BASE_URL}/api/discharged/summary", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return 'risk_level' in data
    except Exception as e:
        print(f"AI summary error: {e}")
    return False

def test_patient_detail():
    try:
        session.post(f"{BASE_URL}/login", data={"staff_id": "DOC0001", "password": "password"}, timeout=10)
        resp = session.get(f"{BASE_URL}/patient/1", timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"Patient detail error: {e}")
    return False

results = {
    "Doctor Login": test_doctor_login(),
    "Nurse Login": test_nurse_login(),
    "Discharged Login": test_discharged_login(),
    "AI Summary": test_ai_summary(),
    "Patient Detail": test_patient_detail(),
}

print("\n=== VERIFICATION RESULTS ===")
for test_name, passed in results.items():
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {test_name}")

passed_count = sum([1 for v in results.values() if v])
total = len(results)
print(f"\n{passed_count}/{total} tests passed\n")
