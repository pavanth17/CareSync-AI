import requests
BASE='http://127.0.0.1:5000'
s=requests.Session()
r=s.post(BASE+'/login', data={'staff_id':'DOC0001','password':'password'}, allow_redirects=True)
print('login status', r.status_code)
print('login headers:', r.headers)
print('login history len:', len(r.history))
print('cookies after login:', s.cookies.get_dict())
resp=s.get(BASE+'/patient/1')
print('patient/1 status', resp.status_code)
print(resp.text[:500])
