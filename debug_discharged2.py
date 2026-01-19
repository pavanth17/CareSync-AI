import requests
s = requests.Session()
resp = s.post('http://127.0.0.1:5000/discharged-portal', data={'patient_id': 'PATDIS001', 'phone': '555-0101'}, timeout=5, allow_redirects=True)
print(f'Status: {resp.status_code}')
print(f'URL: {resp.url}')
print(f'Has CareSync: {"CareSync" in resp.text}')
print(f'First 300 chars: {resp.text[:300]}')
