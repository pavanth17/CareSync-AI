import requests
s = requests.Session()
resp = s.post('http://127.0.0.1:5000/discharged-portal', data={'patient_id': 'PATDIS001', 'phone': '555-0101'}, timeout=5, allow_redirects=False)
print(f'Status: {resp.status_code}')
print(f'Redirect: {resp.is_redirect}')
print(f'Location: {resp.headers.get("Location", "N/A")}')
if resp.status_code >= 400:
    print(f'Error text: {resp.text[:200]}')
