from app import app
import routes

with app.test_client() as c:
    r = c.get('/')
    print('STATUS', r.status_code)
    data = r.get_data(as_text=True)
    print('\n--- BODY (first 800 chars) ---\n')
    print(data[:800])
