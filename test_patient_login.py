import requests

url = 'http://localhost:5000/patient-login'
data = {
    'patient_id': 'PAT000001',
    'phone': '555-935-4604'
}

try:
    response = requests.post(url, data=data, allow_redirects=False)
    print(f'Status Code: {response.status_code}')
    print(f'Location: {response.headers.get("Location", "N/A")}')
    if response.status_code >= 400:
        print(f'Response: {response.text[:500]}')
except Exception as e:
    print(f'Error: {e}')
